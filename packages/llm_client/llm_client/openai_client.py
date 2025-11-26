from __future__ import annotations

from typing import Optional

from openai import AsyncOpenAI

from .base import ILLMClient, LLMClientConfig


class OpenAIClient(ILLMClient):
    """
    Thin wrapper around OpenAI's async Chat Completions API.
    """

    def __init__(
        self,
        *,
        api_key: str,
        config: Optional[LLMClientConfig] = None,
        model: Optional[str] = None,
    ) -> None:
        if not api_key:
            raise ValueError("OpenAIClient requires a non-empty api_key")

        self.client = AsyncOpenAI(api_key=api_key)
        self.config = config or LLMClientConfig()
        if model:
            self.config.model = model

    async def complete(
        self,
        *,
        system: Optional[str] = None,
        user: Optional[str] = None,
        format: Optional[str] = None,
    ) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        if user:
            messages.append({"role": "user", "content": user})

        if not messages:
            raise ValueError("OpenAIClient.complete requires at least one message")

        params = {
            "model": self.config.model,
            "messages": messages,
            "temperature": self.config.temperature,
        }
        if self.config.max_tokens is not None:
            params["max_tokens"] = self.config.max_tokens
        if format == "json":
            params["response_format"] = {"type": "json_object"}

        response = await self.client.chat.completions.create(**params)
        choice = response.choices[0]
        content = choice.message.content
        if content is None:
            return ""
        if isinstance(content, list):
            # When OpenAI returns structured content (tool calls, etc.),
            # join textual fragments.
            return " ".join(part if isinstance(part, str) else str(part) for part in content)
        return content
