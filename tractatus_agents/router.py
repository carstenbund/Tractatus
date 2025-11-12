"""Routing logic for CLI agent commands."""
from __future__ import annotations

from collections.abc import Iterable
from enum import Enum
from typing import Protocol

from .llm import LLMAgent, LLMResponse


class AgentAction(str, Enum):
    """LLM driven actions that can be triggered from the CLI."""

    COMMENT = "comment"
    COMPARISON = "comparison"
    WEBSEARCH = "websearch"
    REFERENCE = "reference"

    @classmethod
    def from_cli_token(cls, token: str | None) -> "AgentAction":
        """Resolve a loose user supplied token to an :class:`AgentAction`."""

        if not token:
            return cls.COMMENT

        lowered = token.strip().lower()
        for action in cls:
            if lowered.startswith(action.value):
                return action
        msg = ", ".join(action.value for action in cls)
        raise ValueError(f"Unknown LLM action '{token}'. Expected one of: {msg}")


class PropositionLike(Protocol):
    """Protocol capturing the attributes we need from a proposition ORM model."""

    name: str
    text: str


class AgentRouter:
    """Delegates CLI agent commands to the configured LLM agent."""

    def __init__(self, llm_agent: LLMAgent | None = None) -> None:
        self._llm_agent = llm_agent or LLMAgent()

    def perform(
        self,
        action: AgentAction,
        propositions: Iterable[PropositionLike] | None,
        *,
        payload: str | None = None,
        language: str | None = None,
    ) -> LLMResponse:
        """Execute an agent action for the supplied propositions or payload.

        Args:
            action: The LLM action to perform
            propositions: Propositions to analyze
            payload: Optional pre-built payload (overrides propositions)
            language: Optional language code (e.g., "de" for German)
        """

        if payload is None:
            if propositions is None:
                raise ValueError("Either propositions or payload must be provided.")
            payload = self._build_payload(propositions)

        if action is AgentAction.COMMENT:
            return self._llm_agent.comment(payload, language=language)
        if action is AgentAction.COMPARISON:
            return self._llm_agent.compare(payload, language=language)
        if action is AgentAction.WEBSEARCH:
            return self._llm_agent.websearch(payload, language=language)
        if action is AgentAction.REFERENCE:
            return self._llm_agent.reference(payload, language=language)

        raise ValueError(f"Unsupported action: {action}")

    @staticmethod
    def _build_payload(propositions: Iterable[PropositionLike]) -> str:
        """Prepare the textual payload that is sent to the LLM backend."""

        blocks: list[str] = []
        for proposition in propositions:
            blocks.append(f"{proposition.name}: {proposition.text}")
        return "\n\n".join(blocks)
