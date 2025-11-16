"""OpenAI-backed LLM client implementation.

This module provides an OpenAI GPT integration for the Tractatus agent system.
It implements the LLMClient protocol using OpenAI's Chat Completions API,
supporting system prompts and configurable token limits.

Environment Variables:
    OPENAI_API_KEY: Required API key for OpenAI API access

Supported Models:
    - gpt-4o-mini (default): Cost-effective model for most tasks
    - gpt-4o: Most capable GPT-4 optimized model
    - gpt-4-turbo: Previous generation flagship model

Usage:
    Set OPENAI_API_KEY environment variable, then the service layer will
    automatically detect and use this client when available.
"""
from __future__ import annotations

import os

from openai import OpenAI

from .llm import LLMClient


class OpenAILLMClient(LLMClient):
    """Concrete LLMClient implementation using OpenAI's GPT models.

    This client uses the OpenAI Chat Completions API to generate philosophical
    commentary and analysis. It supports both system and user prompts,
    with configurable token limits for response length.

    Attributes:
        client: OpenAI API client instance
        model: Model identifier (e.g., "gpt-4o-mini")
    """

    def __init__(self, model: str = "gpt-4o-mini") -> None:
        """Initialize the OpenAI client with API credentials.

        Args:
            model: GPT model identifier. Defaults to gpt-4o-mini.

        Raises:
            RuntimeError: If OPENAI_API_KEY environment variable is not set

        Example:
            client = OpenAILLMClient()  # Uses default gpt-4o-mini model
            client = OpenAILLMClient(model="gpt-4o")  # Use more capable model
        """
        key = os.getenv("OPENAI_API_KEY")
        if not key:
            raise RuntimeError(
                "Missing OPENAI_API_KEY. Export it before launching the CLI or web app."
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
        """Generate completion using OpenAI API with optional system prompt.

        Supports both legacy single-prompt format and modern system+user format.
        If max_tokens is not specified, defaults to 2000 for quality philosophical
        analysis (increased from previous 600 default to prevent truncation).

        Args:
            prompt: Legacy single-string prompt (converted to user message)
            system: System prompt providing context and instructions
            user: User prompt with the specific request
            max_tokens: Maximum tokens in response (defaults to 2000 for quality analysis)

        Returns:
            Generated text response from GPT

        Raises:
            ValueError: If neither prompt nor system/user is provided

        Example:
            response = client.complete(
                system="You are a philosophy expert.",
                user="Explain proposition 1.1",
                max_tokens=1500
            )
        """
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

        # Call OpenAI Chat Completions API
        # Default to 2000 tokens for quality philosophical analysis (prevents truncation)
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=max_tokens if max_tokens else 2000,
        )
        return response.choices[0].message.content.strip()
