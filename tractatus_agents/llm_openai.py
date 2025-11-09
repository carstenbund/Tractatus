"""OpenAI-backed LLM client implementation."""
from __future__ import annotations

import os

from openai import OpenAI

from .llm import LLMClient


class OpenAILLMClient(LLMClient):
    """Concrete :class:`LLMClient` that talks to the OpenAI API."""

    def __init__(self, model: str = "gpt-4o-mini") -> None:
        key = os.getenv("OPENAI_API_KEY")
        if not key:
            raise RuntimeError(
                "Missing OPENAI_API_KEY. Export it before launching the CLI."
            )
        self.client = OpenAI(api_key=key)
        self.model = model

    def complete(self, prompt: str, *, max_tokens: int | None = None) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens or 600,
        )
        return response.choices[0].message.content.strip()
