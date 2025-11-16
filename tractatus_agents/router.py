"""Routing logic for LLM agent commands.

This module provides a clean abstraction for routing user requests to appropriate
LLM-powered analysis functions. It decouples the high-level service layer from
the specific LLM implementation details.

Architecture:
    AgentAction: Enum defining available AI analysis types
    PropositionLike: Protocol for duck-typed proposition objects
    AgentRouter: Main router that delegates to LLMAgent methods

The router pattern allows for easy extension of analysis types and swapping
of LLM backends without affecting the rest of the application.
"""
from __future__ import annotations

from collections.abc import Iterable
from enum import Enum
from typing import Protocol

from .llm import LLMAgent, LLMResponse


class AgentAction(str, Enum):
    """Available LLM-powered analysis actions for philosophical text.

    These actions represent different types of AI analysis that can be
    performed on Tractatus propositions. Each action corresponds to a
    specific method on the LLMAgent class.

    Actions:
        COMMENT: Generate philosophical commentary on a single proposition
        COMPARISON: Compare and analyze relationships between multiple propositions
        WEBSEARCH: Search the web for related context (future feature)
        REFERENCE: Find and analyze references to related propositions (future feature)
    """

    COMMENT = "comment"
    COMPARISON = "comparison"
    WEBSEARCH = "websearch"
    REFERENCE = "reference"

    @classmethod
    def from_cli_token(cls, token: str | None) -> "AgentAction":
        """Parse a user-supplied string into an AgentAction enum.

        Accepts partial matches and case-insensitive input for user convenience.
        For example, "comp", "COMP", or "comparison" all match COMPARISON.

        Args:
            token: User input string (e.g., "comment", "comp", None)

        Returns:
            Matching AgentAction enum value

        Raises:
            ValueError: If token doesn't match any known action

        Examples:
            from_cli_token("comment") -> AgentAction.COMMENT
            from_cli_token("comp") -> AgentAction.COMPARISON
            from_cli_token(None) -> AgentAction.COMMENT (default)
        """

        # Default to COMMENT if no token provided
        if not token:
            return cls.COMMENT

        # Try to match against action values (case-insensitive, prefix match)
        lowered = token.strip().lower()
        for action in cls:
            if lowered.startswith(action.value):
                return action

        # No match found - raise error with helpful message
        msg = ", ".join(action.value for action in cls)
        raise ValueError(f"Unknown LLM action '{token}'. Expected one of: {msg}")


class PropositionLike(Protocol):
    """Protocol for duck-typed proposition objects.

    This protocol defines the minimal interface required for proposition objects
    used by the agent router. Using a Protocol instead of concrete types allows
    the router to work with any object that has `name` and `text` attributes,
    promoting loose coupling and testability.

    This is an example of structural subtyping (duck typing with type hints),
    which is more flexible than nominal subtyping (inheritance-based).

    Attributes:
        name: Hierarchical address (e.g., "1.1", "2.0121")
        text: The proposition text content
    """

    name: str
    text: str


class AgentRouter:
    """Routes LLM agent requests to appropriate analysis methods.

    The router acts as a facade over the LLMAgent, providing a clean interface
    for the service layer to invoke AI-powered analysis without knowing the
    details of prompt construction, API calls, or response handling.

    This design pattern provides:
    - Separation of concerns (routing logic vs. LLM interaction)
    - Easy testing (can inject mock LLMAgent)
    - Flexibility to switch LLM backends

    Attributes:
        _llm_agent: The underlying LLM agent that performs the actual analysis
    """

    def __init__(self, llm_agent: LLMAgent | None = None) -> None:
        """Initialize the router with an LLM agent.

        Args:
            llm_agent: Optional LLMAgent instance. If None, creates a default agent.
        """
        self._llm_agent = llm_agent or LLMAgent()

    def perform(
        self,
        action: AgentAction,
        propositions: Iterable[PropositionLike] | None,
        *,
        payload: str | None = None,
        language: str | None = None,
        user_input: str | None = None,
    ) -> LLMResponse:
        """Execute an LLM agent action for the specified propositions.

        This is the main entry point for all AI-powered analysis. It routes
        the action to the appropriate LLMAgent method based on the action type.

        Args:
            action: The type of analysis to perform (comment, comparison, etc.)
            propositions: Propositions to analyze (can be None if payload is provided)
            payload: Optional pre-formatted text payload (overrides propositions)
                    Useful when the caller has already formatted the text
            language: Optional language code for analysis ("de", "en", etc.)
            user_input: Optional user-provided prompt to guide the analysis

        Returns:
            LLMResponse containing the AI-generated analysis

        Raises:
            ValueError: If neither propositions nor payload is provided
            ValueError: If action is not recognized (should not happen with enum)

        Examples:
            # Comment on a single proposition
            router.perform(AgentAction.COMMENT, [prop1], language="en")

            # Compare multiple propositions
            router.perform(AgentAction.COMPARISON, [prop1, prop2], language="de")

            # Use pre-built payload
            router.perform(AgentAction.COMMENT, None, payload="1: Text here")
        """

        # Build text payload from propositions if not already provided
        if payload is None:
            if propositions is None:
                raise ValueError("Either propositions or payload must be provided.")
            payload = self._build_payload(propositions)

        # Route to appropriate LLM method based on action type
        if action is AgentAction.COMMENT:
            return self._llm_agent.comment(payload, language=language, user_input=user_input)
        if action is AgentAction.COMPARISON:
            return self._llm_agent.compare(payload, language=language, user_input=user_input)
        if action is AgentAction.WEBSEARCH:
            return self._llm_agent.websearch(payload, language=language, user_input=user_input)
        if action is AgentAction.REFERENCE:
            return self._llm_agent.reference(payload, language=language, user_input=user_input)

        # Should never reach here with proper enum usage
        raise ValueError(f"Unsupported action: {action}")

    @staticmethod
    def _build_payload(propositions: Iterable[PropositionLike]) -> str:
        """Build a formatted text payload from proposition objects.

        Converts proposition objects into a standardized text format for the LLM.
        Each proposition is formatted as "name: text" with double newlines
        between propositions for clarity.

        Args:
            propositions: Iterable of proposition objects

        Returns:
            Formatted text string ready for LLM processing

        Example:
            Input: [Proposition(name="1", text="Die Welt..."),
                   Proposition(name="1.1", text="Die Welt...")]
            Output: "1: Die Welt...\n\n1.1: Die Welt..."
        """

        blocks: list[str] = []
        for proposition in propositions:
            blocks.append(f"{proposition.name}: {proposition.text}")
        return "\n\n".join(blocks)
