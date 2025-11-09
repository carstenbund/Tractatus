"""Lightweight LLM abstraction used by the CLI agent commands."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class LLMClient(Protocol):
    """Minimal protocol that any concrete LLM backend must implement."""

    def complete(self, prompt: str, *, max_tokens: int | None = None) -> str:  # pragma: no cover - protocol definition
        """Return the generated text for the supplied prompt."""


@dataclass(slots=True)
class LLMResponse:
    """Structured response returned to the CLI after an agent invocation."""

    action: str
    content: str
    prompt: str


class EchoLLMClient:
    """Fallback client that echoes the prompt when no backend is configured."""

    def complete(self, prompt: str, *, max_tokens: int | None = None) -> str:  # noqa: D401 - short delegation
        return (
            "[Placeholder LLM]\n"
            "No LLM backend is configured. Provide OPENAI_API_KEY or inject a custom "
            "LLM client.\n\nPrompt received:\n"
            f"{prompt}"
        )


class LLMAgent:
    """Encapsulates prompt engineering for the different CLI agent actions."""

    def __init__(self, client: LLMClient | None = None, *, max_tokens: int | None = 500) -> None:
        self._client = client or EchoLLMClient()
        self._max_tokens = max_tokens

    def comment(self, payload: str) -> LLMResponse:
        prompt = self._format_prompt(
            "Provide a reflective commentary on the following Tractatus propositions.",
            payload,
        )
        return self._ask("Comment", prompt)

    def compare(self, payload: str) -> LLMResponse:
        prompt = self._format_prompt(
            "Compare the following Tractatus propositions, focusing on interpretive contrasts and logical flow.",
            payload,
        )
        return self._ask("Comparison", prompt)

    def websearch(self, payload: str) -> LLMResponse:
        prompt = self._format_prompt(
            "Suggest web-search queries and summarize potential online resources that contextualize these propositions.",
            payload,
        )
        return self._ask("Websearch", prompt)

    def reference(self, payload: str) -> LLMResponse:
        prompt = self._format_prompt(
            "List relevant philosophical references or academic sources that expand on these propositions.",
            payload,
        )
        return self._ask("Reference", prompt)

    def _ask(self, action: str, prompt: str) -> LLMResponse:
        content = self._client.complete(prompt, max_tokens=self._max_tokens)
        return LLMResponse(action=action, content=content, prompt=prompt)

    @staticmethod
    def _format_prompt(instruction: str, payload: str) -> str:
        return f"{instruction}\n\n{payload}".strip()
