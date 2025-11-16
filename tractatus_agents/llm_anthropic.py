"""Anthropic-backed LLM client implementation.

This module provides an Anthropic Claude integration for the Tractatus agent system.
It implements the LLMClient protocol using Anthropic's Messages API, supporting
system prompts and configurable token limits.

Environment Variables:
    ANTHROPIC_API_KEY: Required API key for Anthropic Claude access

Supported Models:
    - claude-3-5-sonnet-20241022 (default): Most capable model for complex reasoning
    - claude-3-5-haiku-20241022: Faster, more cost-effective option
    - claude-3-opus-20240229: Previous generation flagship model

Usage:
    Set ANTHROPIC_API_KEY environment variable, then the service layer will
    automatically detect and use this client when available.
"""
from __future__ import annotations

import os

from anthropic import Anthropic

from .llm import LLMClient


class AnthropicLLMClient(LLMClient):
    """Concrete LLMClient implementation using Anthropic's Claude models.

    This client uses the Anthropic Messages API to generate philosophical
    commentary and analysis. It supports both system and user prompts,
    with configurable token limits for response length.

    Attributes:
        client: Anthropic API client instance
        model: Model identifier (e.g., "claude-3-5-sonnet-20241022")
    """

    def __init__(self, model: str = "claude-3-5-sonnet-20241022") -> None:
        """Initialize the Anthropic client with API credentials.

        Args:
            model: Claude model identifier. Defaults to Claude 3.5 Sonnet.

        Raises:
            RuntimeError: If ANTHROPIC_API_KEY environment variable is not set

        Example:
            client = AnthropicLLMClient()  # Uses default Sonnet model
            client = AnthropicLLMClient(model="claude-3-5-haiku-20241022")  # Faster model
        """
        key = os.getenv("ANTHROPIC_API_KEY")
        if not key:
            raise RuntimeError(
                "Missing ANTHROPIC_API_KEY. Export it before launching the CLI or web app."
            )
        self.client = Anthropic(api_key=key)
        self.model = model

    def complete(
        self,
        prompt: str | None = None,
        *,
        system: str | None = None,
        user: str | None = None,
        max_tokens: int | None = None,
    ) -> str:
        """Generate completion using Anthropic Claude with optional system prompt.

        Supports both legacy single-prompt format and modern system+user format.
        The Anthropic API requires explicit max_tokens, so we provide sensible
        defaults if not specified.

        Args:
            prompt: Legacy single-string prompt (converted to user message)
            system: System prompt providing context and instructions
            user: User prompt with the specific request
            max_tokens: Maximum tokens in response (defaults to 2000 for quality analysis)

        Returns:
            Generated text response from Claude

        Raises:
            ValueError: If neither prompt nor system/user is provided

        Example:
            response = client.complete(
                system="You are a philosophy expert.",
                user="Explain proposition 1.1",
                max_tokens=1500
            )
        """
        # Build messages array for Anthropic API
        messages = []

        # Support both legacy single-prompt and new system+user format
        if user or prompt:
            # Use user parameter if provided, otherwise fall back to legacy prompt
            content = user if user else prompt
            if content:
                messages.append({"role": "user", "content": content})
        else:
            raise ValueError("Either 'prompt' or 'user' must be provided.")

        # Anthropic requires explicit max_tokens
        # Default to 2000 for quality philosophical analysis (higher than OpenAI default)
        token_limit = max_tokens if max_tokens else 2000

        # Build API request parameters
        api_params = {
            "model": self.model,
            "messages": messages,
            "max_tokens": token_limit,
        }

        # Add system prompt if provided (Anthropic uses separate system parameter)
        if system:
            api_params["system"] = system

        # Call Anthropic Messages API
        response = self.client.messages.create(**api_params)

        # Extract text from response
        # Anthropic returns content as a list of content blocks
        if response.content and len(response.content) > 0:
            return response.content[0].text.strip()

        return ""
