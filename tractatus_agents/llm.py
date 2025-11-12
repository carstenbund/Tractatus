"""Lightweight LLM abstraction used by the CLI agent commands."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .prompts import build_prompt_pair


class LLMClient(Protocol):
    """Minimal protocol that any concrete LLM backend must implement."""

    def complete(
        self,
        prompt: str | None = None,
        *,
        system: str | None = None,
        user: str | None = None,
        max_tokens: int | None = None,
    ) -> str:  # pragma: no cover - protocol definition
        """
        Return the generated text for the supplied prompt(s).

        Args:
            prompt: Legacy single-string prompt (for backward compatibility)
            system: System prompt providing context and instructions
            user: User prompt with the specific request
            max_tokens: Maximum tokens in the response

        Either 'prompt' or both 'system'/'user' must be provided.
        """


@dataclass(slots=True)
class LLMResponse:
    """Structured response returned to the CLI after an agent invocation."""

    action: str
    content: str
    prompt: str


class EchoLLMClient:
    """Fallback client that echoes the prompt when no backend is configured."""

    def complete(
        self,
        prompt: str | None = None,
        *,
        system: str | None = None,
        user: str | None = None,
        max_tokens: int | None = None,
    ) -> str:  # noqa: D401 - short delegation
        # Build display of what was sent
        if system or user:
            prompt_display = ""
            if system:
                prompt_display += f"System:\n{system}\n\n"
            if user:
                prompt_display += f"User:\n{user}"
        else:
            prompt_display = prompt or ""

        return (
            "[Placeholder LLM]\n"
            "No LLM backend is configured. Provide OPENAI_API_KEY or inject a custom "
            "LLM client.\n\nPrompt received:\n"
            f"{prompt_display}"
        )


class LLMAgent:
    """Encapsulates prompt engineering for the different CLI agent actions."""

    def __init__(self, client: LLMClient | None = None, *, max_tokens: int | None = 500) -> None:
        self._client = client or EchoLLMClient()
        self._max_tokens = max_tokens

    def comment(self, payload: str, language: str | None = None) -> LLMResponse:
        prompt_pair = build_prompt_pair("comment", payload, language=language)
        return self._ask("Comment", prompt_pair)

    def compare(self, payload: str, language: str | None = None) -> LLMResponse:
        prompt_pair = build_prompt_pair("comparison", payload, language=language)
        return self._ask("Comparison", prompt_pair)

    def websearch(self, payload: str, language: str | None = None) -> LLMResponse:
        prompt_pair = build_prompt_pair("websearch", payload, language=language)
        return self._ask("Websearch", prompt_pair)

    def reference(self, payload: str, language: str | None = None) -> LLMResponse:
        prompt_pair = build_prompt_pair("reference", payload, language=language)
        return self._ask("Reference", prompt_pair)

    def _ask(self, action: str, prompt_pair: dict[str, str]) -> LLMResponse:
        """Ask the LLM using system + user prompt pair."""
        content = self._client.complete(
            system=prompt_pair["system"],
            user=prompt_pair["user"],
            max_tokens=self._max_tokens,
        )
        # For response logging, concatenate system and user
        full_prompt = f"{prompt_pair['system']}\n\n{prompt_pair['user']}"
        return LLMResponse(action=action, content=content, prompt=full_prompt)
