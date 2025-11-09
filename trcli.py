import cmd
import re
import shlex
from collections.abc import Iterable
from typing import TYPE_CHECKING

from sqlalchemy import select, text
from tractatus_agents import AgentAction, AgentRouter
from tractatus_agents.llm import LLMAgent
from tractatus_orm.database import SessionLocal, init_db
from tractatus_orm.models import Proposition, Translation

if TYPE_CHECKING:
    from tractatus_agents.llm import LLMResponse


class TractatusCLI(cmd.Cmd):
    intro = "Tractatus ORM CLI. Type help or ? to list commands.\n"
    prompt = "(tractatus) "

    def __init__(self):
        super().__init__()
        init_db()
        self.session = SessionLocal()
        self.current: Proposition | None = None
        self.agent_router = self._configure_agent_router()
            
    def default(self, line: str):
        """Fallback for unknown input — interpret bare numbers or ag: forms."""
    
        text = line.strip()
        if not text:
            return  # ignore empty lines
    
        if text.startswith("ag:"):
            # handle "ag:1" or "ag:1-2" or "ag:1:2" etc.
            remainder = text[3:].strip()  # directly slice after "ag:"
            if not remainder:
                print("Usage: ag:<target> [action]")
                return
            return self.do_agent(remainder)

        # --- 2. handle inline agent "X ag[:<action>]" or "X ag:<action>" ---
        # e.g. "1 ag" or "1 ag:compare" or "1 ag:comment"
        if " ag" in text:
            head, tail = text.split(" ag", 1)
            head = head.strip()
            tail = tail.lstrip(":").strip()  # remove optional colon
            # Execute the first part if it looks like a navigation
            if head:
                stop = self.onecmd(head)
                if stop:
                    return stop
            if tail:
                # tail could be just an action, e.g. "compare"
                return self.do_agent(f"{head} {tail}".strip())
            else:
                # no explicit mode → default to comment
                return self.do_agent(head.strip())
    
        # --- 3. support compact range queries like "1-2" or "1:2" ---
        if re.match(r"^\d+(\.\d+)*\s*[-:]\s*\d+(\.\d+)*$", text):
            return self.do_get(text)
    
        # --- 4. treat bare number-like input as 'get' ---
        if text[0].isdigit() or text.startswith("id:") or text.startswith("name:"):
            return self.do_get(text)
    
        # --- 5. nothing matched ---
        print(f"Unknown syntax: {line}")
       

    def do_get(self, arg):
        """get <value> — jump by name (default) or id:<n> if explicit"""
        key = arg.strip()
        if not key:
            print("Usage: get <name> or get id:<n>")
            return
        
        # --- explicit id override ---
        if key.startswith("id:"):
            try:
                value = int(key.removeprefix("id:"))
            except ValueError:
                print("Invalid id syntax. Use: get id:<integer>")
                return
            chosen = self.session.get(Proposition, value)
            if not chosen:
                print(f"No record found for id {value}")
                return
            self.current = chosen
            print(f"(id) {chosen.name}: {chosen.text}")
            return
        
        # --- default: name-first resolution ---
        name_hit = self.session.scalars(
            select(Proposition).where(Proposition.name == key)
        ).first()
        
        if name_hit:
            self.current = name_hit
            print(f"{name_hit.name}: {name_hit.text}")
            return
        
        # fallback: id lookup only if name not found
        if key.isdigit():
            id_hit = self.session.get(Proposition, int(key))
            if id_hit:
                print(f"(fallback by id) {id_hit.name}: {id_hit.text}")
                self.current = id_hit
                return
            
        print(f"No proposition found for '{key}'.")
        

    def do_parent(self, arg):
        """Show parent of current node"""
        if not self.current or not self.current.parent_id:
            print("No parent.")
            return
        parent = self.session.get(Proposition, self.current.parent_id)
        print(parent)
        self.current = parent

    def do_children(self, arg):
        """List children"""
        if not self.current:
            print("No current node.")
            return
        for child in self.current.children:
            print(f"{child.id:>4}  {child.name}: {child.text[:60]}")

    def do_list(self, arg):
        """list [name] — list children for the target or current node."""

        target = arg.strip()
        if target:
            node = self.session.scalars(
                select(Proposition).where(Proposition.name == target)
            ).first()
            if not node:
                print(f"No proposition found for '{target}'.")
                return
            self.current = node
        elif not self.current:
            print("No current node.")
            return

        node = self.current
        children = sorted(node.children, key=lambda child: self._sort_key(child.name))
        if not children:
            print("No children.")
            return
        for child in children:
            print(f"{child.id:>4}  {child.name}: {child.text[:60]}")

    def do_tree(self, arg):
        """Recursively print subtree"""
        if not self.current:
            print("No current node.")
            return

        def print_tree(node, depth=0):
            print("  " * depth + f"{node.name}: {node.text}")
            for ch in node.children:
                print_tree(ch, depth + 1)

        print_tree(self.current)

    # --- translations ---
    def do_translations(self, arg):
        """List translations of current node"""
        if not self.current:
            print("No current node.")
            return
        for t in self.current.translations:
            print(f"[{t.lang}] {t.text[:60]} ({t.source or 'unknown'})")

    def do_translate(self, arg):
        """translate <lang> — show translation text"""
        if not self.current:
            print("No current node.")
            return
        lang = arg.strip()
        if not lang:
            print("Usage: translate <lang>")
            return
        stmt = select(Translation).where(
            Translation.tractatus_id == self.current.id,
            Translation.lang == lang
        )
        t = self.session.scalars(stmt).first()
        if t:
            print(t.text)
        else:
            print("No translation found.")

    # --- utility commands ---
    def do_search(self, arg):
        """search <term> — find propositions containing term"""
        term = f"%{arg.strip()}%"
        stmt = select(Proposition).where(Proposition.text.ilike(term))
        for p in self.session.scalars(stmt):
            print(f"{p.name}: {p.text[:60]}")

    def do_sql(self, arg):
        """sql <query> — execute raw SQL"""
        for row in self.session.execute(text(arg)):
            print(row)

    def do_exit(self, arg):
        """Exit"""
        print("Goodbye.")
        self.session.close()
        return True

    # --- agent integrations ---
    def do_ag(self, arg: str):
        """ag [target] [mode] — convenience wrapper for agent invocation."""

        return self.do_agent(arg)

    def do_agent(self, arg: str):
        """Hybrid agent command supporting prefixes and inline usage."""

        arg = arg.strip()
        tokens = shlex.split(arg)

        if not tokens:
            return self._agent_on_current(AgentAction.COMMENT)

        command_map = {
            "get": self._agent_payload_for_targets,
            "list": self._agent_payload_for_list,
            "tree": self._agent_payload_for_tree,
        }

        first_token = tokens[0]
        command_key = first_token.lower()

        try:
            if command_key in command_map:
                action, remaining = self._split_action_token(tokens[1:])
                payload_info = command_map[command_key](remaining)
            else:
                action, target_tokens = self._split_action_token(tokens)
                if not target_tokens:
                    return self._agent_on_current(action)
                payload_info = self._agent_payload_for_targets(target_tokens)
        except ValueError as exc:
            print(exc)
            return

        if not payload_info:
            return

        propositions, payload, scope = payload_info
        response = self.agent_router.perform(action, propositions, payload=payload)
        self._display_agent_response(response, scope)

    @staticmethod
    def _split_action_token(tokens: list[str]) -> tuple[AgentAction, list[str]]:
        if not tokens:
            return AgentAction.COMMENT, tokens

        candidate = tokens[-1]
        try:
            action = AgentAction.from_cli_token(candidate)
        except ValueError:
            return AgentAction.COMMENT, tokens
        return action, tokens[:-1]

    def _agent_on_current(self, action: AgentAction) -> None:
        if not self.current:
            print("No current node.")
            return
        propositions = [self.current]
        response = self.agent_router.perform(action, propositions)
        scope = self._format_proposition_scope(propositions)
        self._display_agent_response(response, scope)

    def _agent_payload_for_targets(
        self, tokens: Iterable[str]
    ) -> tuple[list[Proposition], str | None, str] | None:
        tokens = [token.strip() for token in tokens if token.strip()]
        if not tokens:
            if not self.current:
                print("No proposition target supplied and no current node.")
                return None
            propositions = [self.current]
        else:
            propositions = self._resolve_agent_tokens(tokens)
        if not propositions:
            joined = " ".join(tokens) if tokens else "<current>"
            print(f"No propositions found for {joined}.")
            return None
        scope = self._format_proposition_scope(propositions)
        return propositions, None, scope

    def _agent_payload_for_list(
        self, tokens: Iterable[str]
    ) -> tuple[list[Proposition], str | None, str] | None:
        token_list = [token.strip() for token in tokens if token.strip()]
        if token_list:
            targets = self._resolve_agent_tokens([token_list[0]])
            if not targets:
                print(f"No propositions found for {token_list[0]}.")
                return None
            node = targets[0]
        else:
            if not self.current:
                print("No current node.")
                return None
            node = self.current
        self.current = node
        children = sorted(node.children, key=lambda child: self._sort_key(child.name))
        if not children:
            print(f"No children found for {node.name}.")
            return None
        payload = "\n\n".join(f"{child.name}: {child.text}" for child in children)
        scope = f"children of {node.name}"
        return list(children), payload, scope

    def _agent_payload_for_tree(
        self, tokens: Iterable[str]
    ) -> tuple[list[Proposition], str | None, str] | None:
        token_list = [token.strip() for token in tokens if token.strip()]
        if token_list:
            targets = self._resolve_agent_tokens([token_list[0]])
            if not targets:
                print(f"No propositions found for {token_list[0]}.")
                return None
            node = targets[0]
        else:
            if not self.current:
                print("No current node.")
                return None
            node = self.current
        self.current = node
        payload = self._render_tree(node)
        scope = f"tree of {node.name}"
        return [node], payload, scope

    def _resolve_agent_tokens(self, tokens: Iterable[str]) -> list[Proposition]:
        collected: dict[int, Proposition] = {}
        for token in tokens:
            try:
                matches = self._resolve_agent_token(token)
            except ValueError as exc:
                print(exc)
                return []
            for proposition in matches:
                collected[proposition.id] = proposition
        ordered = sorted(collected.values(), key=lambda prop: self._sort_key(prop.name))
        if ordered:
            self.current = ordered[0]
        return ordered

    def _resolve_agent_token(self, token: str) -> list[Proposition]:
        token = token.strip()
        if not token:
            return []
        if token.startswith("id:"):
            try:
                identifier = int(token.removeprefix("id:"))
            except ValueError:
                raise ValueError("Invalid id syntax. Use id:<integer>.") from None
            proposition = self.session.get(Proposition, identifier)
            return [proposition] if proposition else []
        start, end = self._parse_agent_range(token)
        if end:
            stmt = (
                select(Proposition)
                .where(Proposition.name >= start, Proposition.name <= end)
                .order_by(Proposition.name)
            )
            return list(self.session.scalars(stmt))
        stmt = select(Proposition).where(Proposition.name == start)
        return list(self.session.scalars(stmt))

    @staticmethod
    def _parse_agent_range(token: str) -> tuple[str, str | None]:
        token = token.strip()
        if not token:
            raise ValueError("Missing proposition target for agent command.")
        for separator in (":", "-"):
            if separator in token:
                start, end = token.split(separator, 1)
                start = start.strip()
                end = end.strip()
                if not start or not end:
                    raise ValueError("Invalid range syntax. Use <start>-<end> or <start>:<end>.")
                return start, end
        return token, None

    @staticmethod
    def _render_tree(node: Proposition) -> str:
        lines: list[str] = []

        def walk(current: Proposition, depth: int = 0) -> None:
            lines.append("  " * depth + f"{current.name}: {current.text}")
            for child in sorted(current.children, key=lambda ch: TractatusCLI._sort_key(ch.name)):
                walk(child, depth + 1)

        walk(node)
        return "\n".join(lines)

    @staticmethod
    def _sort_key(name: str) -> list[int | str]:
        return [int(part) if part.isdigit() else part for part in re.split(r"(\d+)", name)]

    def _format_proposition_scope(self, propositions: Iterable[Proposition]) -> str:
        names = {p.name for p in propositions}
        ordered = ", ".join(sorted(names, key=self._sort_key))
        return ordered

    def _display_agent_response(self, response: "LLMResponse", scope: str | None = None) -> None:
        if scope:
            print(f"[LLM] {response.action} for {scope}")
        else:
            print(f"[LLM] {response.action}")
        print(response.content)

    def _configure_agent_router(self) -> AgentRouter:
        """Create an agent router with the preferred LLM backend."""

        client = None
        try:
            from tractatus_agents.llm_openai import OpenAILLMClient
        except ImportError:  # pragma: no cover - optional dependency
            print(
                "OpenAI backend unavailable (missing 'openai' package?). "
                "Falling back to echo client.",
            )
        else:
            try:
                client = OpenAILLMClient()
            except RuntimeError as exc:
                print(f"{exc} Falling back to echo client.")
            except Exception as exc:  # pragma: no cover - defensive guard
                print(f"Unable to initialise OpenAI client: {exc}. Falling back to echo client.")

        return AgentRouter(LLMAgent(client))


if __name__ == "__main__":
    TractatusCLI().cmdloop()

    
