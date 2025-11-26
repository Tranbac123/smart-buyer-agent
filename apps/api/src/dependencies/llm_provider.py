# apps/api/src/dependencies/llm_provider.py
from __future__ import annotations

from functools import lru_cache
from typing import Optional, List, Callable
import logging

from config.settings import settings
from packages.llm_client.llm_client.base import ILLMClient, LLMClientConfig  # type: ignore
from packages.llm_client.llm_client.local_client import LocalClient  # type: ignore

logger = logging.getLogger("quantumx.llm_provider")


def _build_openai_client() -> Optional[ILLMClient]:
    """
    Try to construct an OpenAI-backed client.
    Returns None if requirements are not satisfied (e.g., missing key or package).
    """
    if not getattr(settings, "OPENAI_ENABLED", False):
        return None
    try:
        from packages.llm_client.llm_client.openai_client import OpenAIClient  # type: ignore
    except Exception as exc:  # pragma: no cover
        logger.warning("OpenAI client import failed: %s", exc)
        return None
    
    api_key = settings.OPENAI_API_KEY.get_secret_value() if settings.OPENAI_API_KEY else None
    if not api_key:
        return None
    cfg = LLMClientConfig(model=getattr(settings, "OPENAI_MODEL", "gpt-4o-mini"))
    return OpenAIClient(api_key=api_key, config=cfg)

def _build_anthropic_client() -> Optional[ILLMClient]:
    """
    Try to construct an Anthropic-backed client.
    Returns None if requirements are not satisfied.
    """
    if not getattr(settings, "ANTHROPIC_ENABLED", False):
        return None
    try:
        from packages.llm_client.llm_client.anthropic_client import AnthropicClient  # type: ignore
    except Exception:
        return None

    api_key = settings.ANTHROPIC_API_KEY.get_secret_value() if settings.ANTHROPIC_API_KEY else None
    if not api_key:
        return None

    return AnthropicClient(api_key=api_key)

def _build_local_client() -> Optional[ILLMClient]:
    """
    Construct a local/dev client. Always succeeds.
    """
    return LocalClient()

@lru_cache(maxsize=1)
def get_llm() -> ILLMClient:
    """
    Dependency provider for an LLM client.

    Selection policy:
      1) Respect settings.LLM_PROVIDER when possible.
      2) If the chosen provider is not available, try the others.
      3) Always fall back to LocalClient to keep the system operable in dev.

    The instance is cached (singleton) for the process lifetime.
    """
    provider = (getattr(settings, "LLM_PROVIDER", "openai") or "openai").lower()

    # Hard preference order based on configured provider
    candidates: List[Callable[[], Optional[ILLMClient]]] = []
    if provider == "openai":
        candidates = [_build_openai_client, _build_anthropic_client, _build_local_client]
    elif provider == "anthropic":
        candidates = [_build_anthropic_client, _build_openai_client, _build_local_client]
    else:  # "local" or unknown
        candidates = [_build_local_client, _build_openai_client, _build_anthropic_client]

    for factory in candidates:
        client = factory()
        if client is not None:
            return client

    # Absolute last resort: raise a clear error
    raise RuntimeError(
        "No available LLM client. Ensure at least one of OpenAI/Anthropic/local clients is installed and configured."
    )