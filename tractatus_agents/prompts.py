"""Prompt engineering for Tractatus agent responses."""
from __future__ import annotations

SYSTEM_PROMPT = (
    "You are a philosophical commentary assistant specializing in "
    "Ludwig Wittgenstein's *Tractatus Logico-Philosophicus*. "
    "You analyze propositions with close attention to their logical structure, "
    "meaning, and tone within the work's conceptual framework. "
    "Write clearly and precisely, in a philosophical style. "
    "Engage deeply with the text's internal logic and implications."
)


def build_prompt_pair(
    action: str,
    payload: str,
    context: str | None = None,
) -> dict[str, str]:
    """
    Build (system, user) prompt pair for the given action and payload.

    Args:
        action: The agent action (comment, compare, websearch, reference)
        payload: The proposition text(s) to analyze
        context: Optional contextual information (parent/children propositions)

    Returns:
        Dictionary with 'system' and 'user' keys for LLM consumption.
    """
    # Optional context hint
    ctx_block = f"\n\nContext:\n{context.strip()}" if context else ""

    # Action-specific user instructions
    action_prompts = {
        "comment": (
            "Interpret the following proposition as a self-contained statement. "
            "Explain its internal logic, sense, and philosophical implication "
            "within Wittgenstein's overall project:"
        ),
        "comparison": (
            "Compare the following propositions with close attention to their "
            "logical forms and philosophical emphases. How do their structures "
            "and implications differ or align within the Tractatus framework:"
        ),
        "websearch": (
            "Suggest web-search queries and summarize potential online resources "
            "that provide historical, biographical, or interpretive context for "
            "understanding these propositions:"
        ),
        "reference": (
            "List relevant philosophical references, academic sources, and "
            "scholarly interpretations that expand on or challenge the meaning "
            "of these propositions:"
        ),
    }

    user_instruction = action_prompts.get(action.lower(), action_prompts["comment"])

    return {
        "system": SYSTEM_PROMPT,
        "user": f"{user_instruction}\n\n{payload.strip()}{ctx_block}",
    }
