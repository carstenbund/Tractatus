"""Service layer for Tractatus CLI operations - shared by CLI and Flask."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from tractatus_agents import AgentAction, AgentRouter
from tractatus_agents.llm import LLMAgent
from tractatus_config import TrcliConfig
from tractatus_orm.models import Proposition, Translation


class TractatusService:
    """Business logic service for Tractatus operations."""

    def __init__(self, session: Session, config: TrcliConfig | None = None):
        """Initialize service with database session and config."""
        self.session = session
        self.config = config or TrcliConfig()
        self.current: Proposition | None = None
        self._agent_router: AgentRouter | None = None

    @property
    def agent_router(self) -> AgentRouter:
        """Lazy-load agent router on first access."""
        if self._agent_router is None:
            self._agent_router = self._configure_agent_router()
        return self._agent_router

    def get(self, key: str) -> dict | None:
        """Navigate to proposition by name or id. Returns proposition data or None."""
        # --- explicit id override ---
        if key.startswith("id:"):
            try:
                value = int(key.removeprefix("id:"))
            except ValueError:
                return {"error": "Invalid id syntax. Use: get id:<integer>"}
            chosen = self.session.get(Proposition, value)
            if not chosen:
                return {"error": f"No record found for id {value}"}
            self.current = chosen
            return self._proposition_to_dict(chosen)

        # --- name-first resolution ---
        name_hit = self.session.scalars(
            select(Proposition).where(Proposition.name == key)
        ).first()

        if name_hit:
            self.current = name_hit
            return self._proposition_to_dict(name_hit)

        # fallback: id lookup only if name not found
        if key.isdigit():
            id_hit = self.session.get(Proposition, int(key))
            if id_hit:
                self.current = id_hit
                return self._proposition_to_dict(id_hit)

        return {"error": f"No proposition found for '{key}'."}

    def parent(self) -> dict | None:
        """Get parent of current proposition."""
        if not self.current or not self.current.parent_id:
            return {"error": "No parent."}
        parent = self.session.get(Proposition, self.current.parent_id)
        if parent:
            self.current = parent
            return self._proposition_to_dict(parent)
        return {"error": "Parent not found."}

    def next(self) -> dict | None:
        """Go to next proposition by id."""
        return self._navigate_adjacent(1)

    def previous(self) -> dict | None:
        """Go to previous proposition by id."""
        return self._navigate_adjacent(-1)

    def _navigate_adjacent(self, offset: int) -> dict | None:
        """Navigate to adjacent proposition."""
        if not self.current:
            return {"error": "No current node."}

        next_id = self.current.id + offset
        next_prop = self.session.get(Proposition, next_id)
        if not next_prop:
            direction = "next" if offset > 0 else "previous"
            return {"error": f"No {direction} proposition."}

        self.current = next_prop
        return self._proposition_to_dict(next_prop)

    def children(self) -> dict | None:
        """List children of current proposition."""
        if not self.current:
            return {"error": "No current node."}

        children = sorted(
            self.current.children,
            key=lambda child: self._sort_key(child.name),
        )
        if not children:
            return {"children": []}

        return {
            "children": [self._proposition_to_dict(child) for child in children]
        }

    def list(self, target: str | None = None) -> dict | None:
        """List children for target or current node."""
        if target:
            node = self.session.scalars(
                select(Proposition).where(Proposition.name == target)
            ).first()
            if not node:
                return {"error": f"No proposition found for '{target}'."}
            self.current = node
        elif not self.current:
            return {"error": "No current node."}

        node = self.current
        children = sorted(node.children, key=lambda child: self._sort_key(child.name))
        if not children:
            return {"children": []}

        return {
            "current": self._proposition_to_dict(node),
            "children": [self._proposition_to_dict(child) for child in children],
        }

    def tree(self, target: str | None = None) -> dict | None:
        """Get tree for target or current node."""
        if target:
            node = self.session.scalars(
                select(Proposition).where(Proposition.name == target)
            ).first()
            if not node:
                return {"error": f"No proposition found for '{target}'."}
            self.current = node
        elif not self.current:
            return {"error": "No current node."}

        node = self.current
        return {
            "current": self._proposition_to_dict(node),
            "tree": self._render_tree_data(node),
        }

    def search(self, term: str) -> dict | None:
        """Search propositions by text."""
        if not term:
            return {"error": "Search term required."}

        search_term = f"%{term.strip()}%"
        stmt = select(Proposition).where(Proposition.text.ilike(search_term))
        results = list(self.session.scalars(stmt))

        return {
            "query": term,
            "count": len(results),
            "results": [self._proposition_to_dict(p) for p in results],
        }

    def translations(self) -> dict | None:
        """Get translations of current proposition."""
        if not self.current:
            return {"error": "No current node."}

        return {
            "proposition": self._proposition_to_dict(self.current),
            "translations": [
                {
                    "lang": t.lang,
                    "text": t.text,
                    "source": t.source or "unknown",
                }
                for t in self.current.translations
            ],
        }

    def translate(self, lang: str) -> dict | None:
        """Get specific translation."""
        if not self.current:
            return {"error": "No current node."}

        if not lang:
            return {"error": "Language code required."}

        stmt = select(Translation).where(
            Translation.tractatus_id == self.current.id,
            Translation.lang == lang,
        )
        t = self.session.scalars(stmt).first()
        if t:
            return {
                "proposition": self._proposition_to_dict(self.current),
                "translation": {
                    "lang": t.lang,
                    "text": t.text,
                    "source": t.source or "unknown",
                },
            }
        return {"error": f"No translation found for language: {lang}"}

    def agent(
        self,
        action: str,
        targets: list[str] | None = None,
    ) -> dict | None:
        """Invoke LLM agent on propositions."""
        try:
            action_enum = AgentAction.from_cli_token(action)
        except ValueError:
            return {
                "error": f"Unknown action: {action}. Expected one of: comment, comparison, websearch, reference"
            }

        # Resolve target propositions
        if targets:
            propositions = self._resolve_targets(targets)
            if not propositions:
                return {"error": f"No propositions found for targets: {targets}"}
        elif self.current:
            propositions = [self.current]
        else:
            return {"error": "No target propositions specified and no current node."}

        # Build payload
        payload = self._build_agent_payload(propositions)

        # Get response from agent
        response = self.agent_router.perform(action_enum, propositions, payload=payload)

        return {
            "action": response.action,
            "propositions": [self._proposition_to_dict(p) for p in propositions],
            "content": response.content,
        }

    def _resolve_targets(self, targets: list[str]) -> list[Proposition]:
        """Resolve target strings to propositions."""
        propositions = []
        for target in targets:
            target = target.strip()
            if not target:
                continue
            stmt = select(Proposition).where(Proposition.name == target)
            prop = self.session.scalars(stmt).first()
            if prop:
                propositions.append(prop)
        return propositions

    def _build_agent_payload(self, propositions: list[Proposition]) -> str:
        """Build text payload for agent from propositions."""
        blocks = [f"{p.name}: {p.text}" for p in propositions]
        return "\n\n".join(blocks)

    def _proposition_to_dict(self, prop: Proposition) -> dict:
        """Convert proposition to dictionary."""
        display_length = self.config.get("display_length")
        return {
            "id": prop.id,
            "name": prop.name,
            "text": prop.text,
            "text_short": prop.text[:display_length],
            "parent_id": prop.parent_id,
            "level": prop.level,
        }

    def _render_tree_data(self, node: Proposition, depth: int = 0) -> list[dict]:
        """Render tree as structured data."""
        items = []
        items.append({
            "depth": depth,
            **self._proposition_to_dict(node),
        })
        for child in sorted(node.children, key=lambda ch: self._sort_key(ch.name)):
            items.extend(self._render_tree_data(child, depth + 1))
        return items

    @staticmethod
    def _sort_key(name: str) -> list[int | str]:
        """Parse proposition name for sorting."""
        import re
        return [int(part) if part.isdigit() else part for part in re.split(r"(\d+)", name)]

    def _configure_agent_router(self) -> AgentRouter:
        """Create agent router with LLM backend."""
        client = None
        try:
            from tractatus_agents.llm_openai import OpenAILLMClient
            client = OpenAILLMClient()
        except (ImportError, RuntimeError, Exception):
            pass

        max_tokens = self.config.get("llm_max_tokens")
        return AgentRouter(LLMAgent(client, max_tokens=max_tokens))
