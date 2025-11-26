from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from pydantic import BaseModel, Field


class LLMClientConfig(BaseModel):
    """
    Common configuration shared by all LLM clients.
    """

    model: str = Field(default="gpt-4o-mini", description="Default model identifier")
    temperature: float = Field(default=0.0, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(
        default=None, description="Optional limit for completion tokens"
    )


class ILLMClient(ABC):
    """
    Minimal interface that every LLM client implementation must follow.
    """

    config: LLMClientConfig

    @abstractmethod
    async def complete(
        self,
        *,
        system: Optional[str] = None,
        user: Optional[str] = None,
        format: Optional[str] = None,
    ) -> str:
        """
        Execute a text completion and return the generated content.

        Arguments:
            system: Optional system prompt.
            user: User input / question.
            format: Optional format hint (e.g. "json").
        """
        raise NotImplementedError