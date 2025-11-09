# llm_openai.py
import os
from openai import OpenAI

class OpenAILLMClient:
    """Concrete LLMClient that uses OpenAI's API."""

    def __init__(self, model: str = "gpt-4o-mini"):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "Set the OPENAI_API_KEY environment variable "
                "to use the OpenAI backend."
            )
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def complete(self, prompt: str, *, max_tokens: int | None = None) -> str:
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens or 500,
        )
        return resp.choices[0].message.content.strip()
