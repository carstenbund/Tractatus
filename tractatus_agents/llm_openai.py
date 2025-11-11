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

    def complete(
        self,
        prompt: str | None = None,
        *,
        system: str | None = None,
        user: str | None = None,
        max_tokens: int | None = None,
    ) -> str:
        """Generate completion using OpenAI API with optional system prompt."""
        messages = []

        # Support both legacy single-prompt and new system+user format
        if system or user:
            if system:
                messages.append({"role": "system", "content": system})
            if user:
                messages.append({"role": "user", "content": user})
        elif prompt:
            messages.append({"role": "user", "content": prompt})
        else:
            raise ValueError("Either 'prompt' or both 'system'/'user' must be provided.")

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=max_tokens or 600,
        )
        return response.choices[0].message.content.strip()
