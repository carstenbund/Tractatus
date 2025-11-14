"""Prompt engineering for Tractatus agent responses."""
from __future__ import annotations

SYSTEM_PROMPT = (
    "You are a philosophical commentary assistant for the Tractatus corpus. "
    "Treat propositions below 7 as belonging to Ludwig Wittgenstein's original "
    "*Tractatus Logico-Philosophicus*. Propositions numbered 7 or above are "
    "part of the continuation titled *Tractatus Logico-Humanus*. "
    "You analyze propositions with close attention to their logical structure, "
    "meaning, and tone within this evolving conceptual framework. "
    "Write clearly and precisely, in a philosophical style. "
    "Engage deeply with the text's internal logic and implications."
)


def build_prompt_pair(
    action: str,
    payload: str,
    context: str | None = None,
    language: str | None = None,
    user_input: str | None = None,
) -> dict[str, str]:
    """
    Build (system, user) prompt pair for the given action and payload.

    Args:
        action: The agent action (comment, compare, websearch, reference)
        payload: The proposition text(s) to analyze
        context: Optional contextual information (parent/children propositions)
        language: Optional language code ("de" for German, "en" for English)
        user_input: Optional user request appended to the prompt

    Returns:
        Dictionary with 'system' and 'user' keys for LLM consumption.
    """
    # Optional context hint
    ctx_block = f"\n\nContext:\n{context.strip()}" if context else ""

    # Language instruction for German output
    lang_instruction = ""
    if language and language.lower() == "de":
        lang_instruction = "\n\n(Please respond in German.)"

    # Action-specific user instructions
    action_prompts = {
        "comment": (
            "Interpret the following proposition as a self-contained statement. "
            "Explain its internal logic, sense, and philosophical implication "
            "within the appropriate Tractatus context described above:"
        ),
        "comparison": (
            "Compare the following propositions with close attention to their "
            "logical forms and philosophical emphases. How do their structures "
            "and implications differ or align within the combined Tractatus framework:"
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

    extra_request = ""
    if user_input:
        extra_request = f"\n\nAdditional request:\n{user_input.strip()}"

    return {
        "system": SYSTEM_PROMPT,
        "user": (
            f"{user_instruction}\n\n{payload.strip()}{ctx_block}{lang_instruction}{extra_request}"
        ),
    }
