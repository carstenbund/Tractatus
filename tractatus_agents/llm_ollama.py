"""Ollama-backed LLM client implementation for local model inference.

This module provides an Ollama integration for the Tractatus agent system.
It implements the LLMClient protocol using Ollama's local API, supporting
system prompts and configurable token limits without requiring API keys.

Requirements:
    - Ollama must be installed and running locally (see https://ollama.ai)
    - At least one model must be pulled (e.g., `ollama pull llama3.2`)

Environment Variables:
    OLLAMA_HOST: Optional custom Ollama server URL (default: http://localhost:11434)
    OLLAMA_MODEL: Optional default model name (default: llama3.2)

Supported Models:
    - llama3.2 (default): Meta's latest Llama model, excellent for reasoning
    - llama3.1: Previous Llama generation
    - mistral: Mistral AI's efficient model
    - phi3: Microsoft's compact but capable model
    - qwen2.5: Alibaba's multilingual model
    - And many more available at https://ollama.ai/library

Usage:
    1. Install Ollama: https://ollama.ai
    2. Pull a model: `ollama pull llama3.2`
    3. Ensure Ollama is running: `ollama serve`
    4. The service layer will automatically detect and use this client

Advantages:
    - No API keys required
    - Complete privacy (all processing local)
    - No usage costs
    - Works offline
    - Fast inference with GPU acceleration
"""
from __future__ import annotations

import os

import ollama

from .llm import LLMClient


class OllamaLLMClient(LLMClient):
    """Concrete LLMClient implementation using Ollama for local inference.

    This client uses the Ollama local API to generate philosophical commentary
    and analysis using open-source models. It supports both system and user
    prompts, with configurable token limits for response length.

    Attributes:
        client: Ollama client instance
        model: Model identifier (e.g., "llama3.2", "mistral")
        host: Ollama server URL (default: http://localhost:11434)
    """

    def __init__(
        self,
        model: str | None = None,
        host: str | None = None,
    ) -> None:
        """Initialize the Ollama client for local model inference.

        Args:
            model: Model identifier. Defaults to OLLAMA_MODEL env var or "llama3.2"
            host: Ollama server URL. Defaults to OLLAMA_HOST env var or local server

        Raises:
            RuntimeError: If Ollama server is not running or model is not available

        Example:
            client = OllamaLLMClient()  # Uses default llama3.2 model
            client = OllamaLLMClient(model="mistral")  # Use Mistral model
            client = OllamaLLMClient(host="http://remote:11434")  # Remote Ollama server
        """
        # Get model name from parameter, env var, or default
        self.model = model or os.getenv("OLLAMA_MODEL", "llama3.2")

        # Get host from parameter, env var, or default
        self.host = host or os.getenv("OLLAMA_HOST", "http://localhost:11434")

        # Create Ollama client with custom host if specified
        if self.host != "http://localhost:11434":
            self.client = ollama.Client(host=self.host)
        else:
            self.client = ollama.Client()

        # Verify Ollama is running and model is available
        try:
            # Try to list models to verify connection
            self.client.list()
        except Exception as e:
            raise RuntimeError(
                f"Cannot connect to Ollama server at {self.host}. "
                f"Ensure Ollama is running with 'ollama serve'. Error: {e}"
            )

    def complete(
        self,
        prompt: str | None = None,
        *,
        system: str | None = None,
        user: str | None = None,
        max_tokens: int | None = None,
    ) -> str:
        """Generate completion using Ollama with optional system prompt.

        Supports both legacy single-prompt format and modern system+user format.
        Uses Ollama's chat API which supports multi-turn conversations and system
        prompts for better context control.

        Args:
            prompt: Legacy single-string prompt (converted to user message)
            system: System prompt providing context and instructions
            user: User prompt with the specific request
            max_tokens: Maximum tokens in response (Ollama uses num_predict parameter)

        Returns:
            Generated text response from the local model

        Raises:
            ValueError: If neither prompt nor user is provided
            RuntimeError: If Ollama generation fails

        Example:
            response = client.complete(
                system="You are a philosophy expert.",
                user="Explain proposition 1.1",
                max_tokens=1500
            )

        Note:
            Ollama's max_tokens is controlled via the 'num_predict' option.
            Default is typically 128, but we use 2000 to match other providers.
        """
        # Build messages array for Ollama chat API
        messages = []

        # Add system message if provided
        if system:
            messages.append({"role": "system", "content": system})

        # Add user message
        if user:
            messages.append({"role": "user", "content": user})
        elif prompt:
            messages.append({"role": "user", "content": prompt})
        else:
            raise ValueError("Either 'prompt' or 'user' must be provided.")

        # Build Ollama options
        options = {}
        if max_tokens:
            # Ollama uses 'num_predict' instead of 'max_tokens'
            options["num_predict"] = max_tokens
        else:
            # Default to 2000 for quality philosophical analysis
            options["num_predict"] = 2000

        try:
            # Call Ollama chat API
            response = self.client.chat(
                model=self.model,
                messages=messages,
                options=options,
            )

            # Extract and return the message content
            if response and "message" in response:
                content = response["message"].get("content", "")
                return content.strip()

            return ""

        except Exception as e:
            # Provide helpful error messages for common issues
            error_msg = str(e).lower()

            if "model" in error_msg and "not found" in error_msg:
                raise RuntimeError(
                    f"Model '{self.model}' not found. "
                    f"Pull it with: ollama pull {self.model}"
                )
            elif "connection" in error_msg or "refused" in error_msg:
                raise RuntimeError(
                    f"Cannot connect to Ollama at {self.host}. "
                    "Ensure Ollama is running with 'ollama serve'."
                )
            else:
                raise RuntimeError(f"Ollama generation failed: {e}")
