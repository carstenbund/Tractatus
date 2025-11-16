"""Service layer for Tractatus CLI operations - shared by CLI and Flask.

This module provides the core business logic for navigating and interacting with
Wittgenstein's Tractatus Logico-Philosophicus. It abstracts database operations
and provides a clean API for both command-line and web interfaces.

Key Features:
    - Hierarchical navigation (get, parent, next, previous, children)
    - Tree and list views of proposition relationships
    - Full-text search across propositions
    - Multilingual translation support
    - Alternative text versions with metadata
    - AI-powered analysis using LLM agents
    - Language-aware text retrieval
    - Protection against cyclic data relationships

Architecture:
    The service maintains navigation state (current proposition) and delegates
    to SQLAlchemy ORM for database access and AgentRouter for AI operations.
    Configuration is managed by TrcliConfig, which persists user preferences.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from tractatus_agents import AgentAction, AgentRouter
from tractatus_agents.llm import LLMAgent
from tractatus_config import TrcliConfig
from tractatus_orm.models import Proposition, Translation


class TractatusService:
    """Core business logic service for Tractatus operations.

    This class provides a stateful API for navigating the hierarchical structure
    of the Tractatus, with support for translations, search, and AI analysis.
    It maintains a "current proposition" that serves as the navigation context.

    Attributes:
        session: SQLAlchemy database session for ORM queries
        config: User configuration with preferences (language, display settings)
        current: Currently selected proposition (navigation context)
    """

    def __init__(self, session: Session, config: TrcliConfig | None = None):
        """Initialize service with database session and configuration.

        Args:
            session: SQLAlchemy database session for ORM queries
            config: Optional user configuration (defaults to TrcliConfig())
        """
        self.session = session
        self.config = config or TrcliConfig()
        # Current proposition serves as navigation context for operations
        self.current: Proposition | None = None
        # Agent router is lazy-loaded on first use to avoid unnecessary initialization
        self._agent_router: AgentRouter | None = None
        self._agent_router_tokens: int | None = None
        self._config_mtime: float | None = self._config_file_mtime()

    @property
    def agent_router(self) -> AgentRouter:
        """Lazy-load agent router on first access."""
        self.sync_preferences()
        current_max_tokens = self.config.get("llm_max_tokens")
        if (
            self._agent_router is None
            or self._agent_router_tokens != current_max_tokens
        ):
            print(
                "[TractatusService] configuring agent router with "
                f"max_tokens={current_max_tokens}"
            )
            self._agent_router = self._configure_agent_router(
                max_tokens=current_max_tokens
            )
            self._agent_router_tokens = current_max_tokens
        return self._agent_router

    def get(self, key: str) -> dict | None:
        """Navigate to a proposition by name or database ID.

        This is the primary navigation method. It accepts proposition names
        like "1", "1.1", "2.0121" or explicit database IDs like "id:42".
        Sets the found proposition as the current navigation context.

        Resolution order:
        1. If key starts with "id:", use database ID lookup
        2. Try matching by proposition name (e.g., "1.1")
        3. If key is all digits, fall back to database ID lookup

        Args:
            key: Proposition name (e.g., "1.1") or database ID (e.g., "id:42")

        Returns:
            Dictionary with proposition data, or error dict if not found

        Examples:
            get("1.1") -> finds proposition named "1.1"
            get("id:42") -> finds proposition with database ID 42
            get("100") -> tries name first, then database ID 100
        """
        # --- explicit id override using "id:" prefix ---
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

        # --- name-first resolution for hierarchical addresses ---
        name_hit = self.session.scalars(
            select(Proposition).where(Proposition.name == key)
        ).first()

        if name_hit:
            self.current = name_hit
            return self._proposition_to_dict(name_hit)

        # fallback: id lookup only if name not found and key is numeric
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
        depth_pref = self.config.get("tree_max_depth")
        max_depth = depth_pref or None
        return {
            "current": self._proposition_to_dict(node),
            "tree": self._render_tree_data(node, max_depth=max_depth),
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

        translations = [
            t
            for t in self.current.translations
            if (t.variant_type or "translation") != "alternative"
        ]

        return {
            "proposition": self._proposition_to_dict(self.current),
            "translations": [
                {
                    "lang": t.lang,
                    "text": t.text,
                    "source": t.source or "unknown",
                }
                for t in translations
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

    def alternatives(self) -> dict | None:
        """Return alternative text variants for the current proposition."""

        if not self.current:
            return {"error": "No current node."}

        alternatives = [
            {
                "id": alt.id,
                "lang": alt.lang,
                "text": alt.text,
                "editor": alt.editor or "",
                "tags": self._split_tags(alt.tags),
                "created_at": self._format_timestamp(alt.created_at),
                "updated_at": self._format_timestamp(alt.updated_at),
            }
            for alt in sorted(
                (t for t in self.current.translations if t.variant_type == "alternative"),
                key=lambda entry: entry.created_at or datetime.min,
            )
        ]

        return {
            "proposition": self._proposition_to_dict(self.current),
            "alternatives": alternatives,
        }

    def create_alternative(
        self,
        text: str,
        *,
        lang: str | None = None,
        editor: str | None = None,
        tags: list[str] | str | None = None,
    ) -> dict | None:
        """Create a new alternative translation for the current proposition."""

        if not self.current:
            return {"error": "No current node."}

        cleaned_text = (text or "").strip()
        if not cleaned_text:
            return {"error": "Alternative text is required."}

        default_lang = (lang or self.config.get("lang") or "en").strip() or "en"

        translation = Translation(
            lang=default_lang.lower(),
            text=cleaned_text,
            source="user",  # Flag as user-provided
            variant_type="alternative",
            editor=(editor or "").strip() or None,
            tags=self._serialise_tags(tags),
        )
        translation.proposition = self.current
        self.session.add(translation)
        self.session.commit()
        self.session.refresh(translation)

        return {
            "proposition": self._proposition_to_dict(self.current),
            "alternative": {
                "id": translation.id,
                "lang": translation.lang,
                "text": translation.text,
                "editor": translation.editor or "",
                "tags": self._split_tags(translation.tags),
                "created_at": self._format_timestamp(translation.created_at),
                "updated_at": self._format_timestamp(translation.updated_at),
            },
        }

    def agent(
        self,
        action: str,
        targets: list[str] | None = None,
        language: str | None = None,
        user_input: str | None = None,
    ) -> dict | None:
        """Invoke an LLM agent to analyze propositions using AI.

        This method provides AI-powered analysis of philosophical texts using
        OpenAI's GPT models. It supports multiple analysis types and can work
        with text in different languages.

        Supported actions:
            - comment: Generate philosophical commentary on a single proposition
            - comparison: Compare and analyze relationships between multiple propositions
            - websearch: Search web for related context (future feature)
            - reference: Find and analyze related propositions (future feature)

        The agent uses language-aware text retrieval to provide analysis in the
        requested language, pulling from translations when available.

        Args:
            action: The agent action (comment, comparison, websearch, reference)
            targets: Optional list of proposition names to analyze (e.g., ["1.1", "1.2"])
                    If not provided, uses the current proposition
            language: Optional language code ("de" for German, "en" for English)
                     Defaults to user's configured language preference
            user_input: Optional user-supplied prompt to guide the analysis
                       This is included alongside the proposition text

        Returns:
            Dictionary with:
                - action: The action performed
                - propositions: List of analyzed propositions
                - content: AI-generated analysis text
                - user_input: The user prompt (if provided)
                - cached: Whether the response came from cache

        Examples:
            agent("comment", targets=["1.1"], language="en")
            -> Generates English commentary on proposition 1.1

            agent("comparison", targets=["1", "2"], user_input="Compare main themes")
            -> Compares propositions 1 and 2 with custom prompt
        """
        # Parse and validate the action string
        try:
            action_enum = AgentAction.from_cli_token(action)
        except ValueError:
            return {
                "error": f"Unknown action: {action}. Expected one of: comment, comparison, websearch, reference"
            }

        # Resolve target propositions from their names
        if targets:
            propositions = self._resolve_targets(targets)
            if not propositions:
                return {"error": f"No propositions found for targets: {targets}"}
        elif self.current:
            # If no targets specified, use the current navigation context
            propositions = [self.current]
        else:
            return {"error": "No target propositions specified and no current node."}

        # Build text payload in the requested language
        lang = language or self.config.get("lang")
        payload = self._build_agent_payload(propositions, language=lang)

        # Invoke the LLM agent through the router
        response = self.agent_router.perform(
            action_enum,
            propositions,
            payload=payload,
            language=lang,
            user_input=user_input,
        )

        # Return structured response with analysis
        return {
            "action": response.action,
            "propositions": [self._proposition_to_dict(p, language=lang) for p in propositions],
            "content": response.content,
            "user_input": user_input or "",
            "cached": getattr(response, "cached", False),
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

    def _build_agent_payload(
        self, propositions: list[Proposition], language: str | None = None
    ) -> str:
        """Build text payload for agent from propositions in specified language."""
        lang = language or self.config.get("lang")
        blocks = []
        for p in propositions:
            text = self._get_text_in_language(p, lang)
            blocks.append(f"{p.name}: {text}")
        return "\n\n".join(blocks)

    def _get_text_in_language(self, prop: Proposition, language: str | None = None) -> str:
        """Get proposition text in specified language.

        Args:
            prop: The proposition
            language: Language code ("de" for German original, "en"/"fr"/"pt" for translations)

        Returns:
            The proposition text in the requested language, or German original if not found.
        """
        lang = (language or self.config.get("lang") or "").lower()

        # German original - return main text
        if lang.startswith("de"):
            return prop.text

        # Supported translations - find the first matching translation
        for prefix in ("en", "fr", "pt"):
            if lang.startswith(prefix):
                for trans in prop.translations:
                    if trans.lang and trans.lang.lower().startswith(prefix):
                        return trans.text
                return prop.text

        # Default to German for unknown languages
        return prop.text

    def _proposition_to_dict(
        self, prop: Proposition, language: str | None = None
    ) -> dict:
        """Convert proposition to dictionary with language-aware text.

        Args:
            prop: The proposition to convert
            language: Optional language code ("de" for German, "en" for English)

        Returns:
            Dictionary with proposition data in the requested language.
        """
        display_length = self.config.get("display_length")
        lang = language or self.config.get("lang")
        text = self._get_text_in_language(prop, lang)
        return {
            "id": prop.id,
            "name": prop.name,
            "text": text,
            "text_short": text[:display_length],
            "parent_id": prop.parent_id,
            "level": prop.level,
            "language": lang.lower()[:2],  # Return the language used
        }

    @staticmethod
    def _serialise_tags(tags: list[str] | str | None) -> str | None:
        """Normalise tag input to a comma-separated string."""

        if tags is None:
            return None

        if isinstance(tags, str):
            raw_items = tags.split(",")
        else:
            raw_items = list(tags)

        cleaned = [item.strip() for item in raw_items if item and item.strip()]
        if not cleaned:
            return None
        unique = list(dict.fromkeys(cleaned).keys())
        return ",".join(unique)

    @staticmethod
    def _split_tags(tags: str | None) -> list[str]:
        if not tags:
            return []
        return [item.strip() for item in tags.split(",") if item.strip()]

    @staticmethod
    def _format_timestamp(value: datetime | None) -> str | None:
        if not value:
            return None
        if isinstance(value, datetime):
            return value.isoformat()
        try:
            return str(value)
        except Exception:
            return None

    def _render_tree_data(
        self,
        node: Proposition,
        depth: int = 0,
        max_depth: int | None = None,
        _visited: set[int] | None = None,
    ) -> list[dict]:
        """Render tree as structured data, protecting against cyclic relations.

        Some rows in the underlying dataset contain accidental self-references
        (e.g. a proposition whose ``parent_id`` matches its own ``id``). Without
        guarding against this, the recursion below would loop forever and the
        ``/api/tree`` endpoint would raise a ``RecursionError``. We therefore
        keep track of nodes visited on the current traversal path and skip any
        repeated entries.
        """

        visited = _visited or set()
        if node.id in visited:
            # Cycle detected – stop recursion on this branch.
            return []

        visited.add(node.id)

        items = [
            {
                "depth": depth,
                **self._proposition_to_dict(node),
            }
        ]

        if max_depth is not None and depth >= max_depth:
            visited.remove(node.id)
            return items

        for child in sorted(node.children, key=lambda ch: self._sort_key(ch.name)):
            items.extend(
                self._render_tree_data(
                    child,
                    depth + 1,
                    max_depth=max_depth,
                    _visited=visited,
                )
            )

        visited.remove(node.id)
        return items

    @staticmethod
    def _sort_key(name: str) -> list[int | str]:
        """Parse proposition name for sorting."""
        import re
        return [int(part) if part.isdigit() else part for part in re.split(r"(\d+)", name)]

    def _configure_agent_router(
        self, max_tokens: int | None = None
    ) -> AgentRouter:
        """Create agent router with LLM backend.

        Attempts to initialize LLM clients in the following priority order:
        1. Anthropic Claude (if ANTHROPIC_API_KEY is set)
        2. OpenAI GPT (if OPENAI_API_KEY is set)
        3. Echo client (fallback when no API keys are configured)

        The first successfully initialized client is used. This allows users
        to choose their preferred LLM provider via environment variables.

        Args:
            max_tokens: Optional token limit override (uses config default if not provided)

        Returns:
            AgentRouter configured with the best available LLM client
        """
        client = None

        # Try Anthropic Claude first (preferred for philosophical analysis)
        try:
            from tractatus_agents.llm_anthropic import AnthropicLLMClient
            client = AnthropicLLMClient()
        except (ImportError, RuntimeError, Exception):
            # Anthropic not available, try OpenAI
            pass

        # Fallback to OpenAI if Anthropic not available
        if client is None:
            try:
                from tractatus_agents.llm_openai import OpenAILLMClient
                client = OpenAILLMClient()
            except (ImportError, RuntimeError, Exception):
                # OpenAI not available, will use Echo client
                pass

        # Get configured max_tokens (defaults to 2000 in config)
        tokens = (
            self.config.get("llm_max_tokens")
            if max_tokens is None
            else max_tokens
        )
        return AgentRouter(LLMAgent(client, max_tokens=tokens))

    # ------------------------------------------------------------------
    # Configuration helpers
    # ------------------------------------------------------------------

    def sync_preferences(self) -> None:
        """Reload preferences if the config file changed on disk."""

        latest_mtime = self._config_file_mtime()
        if latest_mtime == self._config_mtime:
            return

        self.config.load()
        self._config_mtime = latest_mtime
        self.invalidate_agent_router_cache()

    def record_config_update(self, key: str | None = None) -> None:
        """Track an in-process preference change and refresh caches as needed."""

        self._config_mtime = self._config_file_mtime()
        if key is None or key == "llm_max_tokens":
            self.invalidate_agent_router_cache()

    def invalidate_agent_router_cache(self) -> None:
        """Clear the cached agent router so it is rebuilt on next use."""

        self._agent_router = None
        self._agent_router_tokens = None

    def _config_file_mtime(self) -> float | None:
        """Return the modification time of the backing config file, if any."""

        config_path = getattr(self.config, "config_file", None)
        if not config_path:
            return None
        try:
            return config_path.stat().st_mtime
        except OSError:
            return None
