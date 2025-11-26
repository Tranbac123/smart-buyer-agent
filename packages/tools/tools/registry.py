# packages/tools/tools/registry.py
from __future__ import annotations

"""
ToolRegistry
------------
A small, production-friendly registry for Agent tools.

Design goals:
- Async-first: tools are expected to expose `async def call(payload: dict) -> dict`.
- Fail-soft: clear, typed errors for unknown tools or bad implementations.
- Minimal surface area: register/get/call/list/has/unregister.
- Extensible: before/after hooks for telemetry/logging if you need them.

Notes:
- If a tool only provides a *sync* `call`, we will invoke it inline (blocking).
  Prefer async tools in production to avoid blocking the event loop.
"""

from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, List, Optional
import asyncio
import inspect
import logging

logger = logging.getLogger("quantumx.tools.registry")

# ---- Public exceptions ------------------------------------------------------


class ToolError(RuntimeError):
    """Base error for tool-related issues."""


class UnknownToolError(ToolError):
    """Raised when a tool name is not registered."""


class InvalidToolError(ToolError):
    """Raised when a registered object does not provide a callable `call` method."""


# ---- Registry ---------------------------------------------------------------


BeforeHook = Callable[[str, Dict[str, Any]], None]
AfterHook = Callable[[str, Dict[str, Any], Optional[Dict[str, Any]], Optional[BaseException]], None]


@dataclass
class ToolRegistry:
    """
    Async-friendly tool registry.

    Typical usage:
        reg = ToolRegistry()
        reg.register("price_compare", PriceCompareTool())
        result = await reg.call("price_compare", {"query": "iphone 15"})

    Hooks:
        reg.before_hooks.append(lambda name, payload: ...)
        reg.after_hooks.append(lambda name, payload, result, error: ...)
    """

    _tools: Dict[str, Any] = field(default_factory=dict)
    before_hooks: List[BeforeHook] = field(default_factory=list)
    after_hooks: List[AfterHook] = field(default_factory=list)

    # -- Management API --

    def register(self, name: str, tool: Any, *, overwrite: bool = True) -> None:
        """
        Register a tool under `name`.

        A valid tool must expose a `call` attribute that is callable. Prefer an
        async `call`. If `overwrite=False` and the name exists, raise.
        """
        if not name or not isinstance(name, str):
            raise InvalidToolError("Tool name must be a non-empty string")

        call_attr = getattr(tool, "call", None)
        if call_attr is None or not callable(call_attr):
            raise InvalidToolError(f"Tool '{name}' must implement a callable 'call(payload) -> result'")

        if not overwrite and name in self._tools:
            raise InvalidToolError(f"Tool '{name}' already registered and overwrite=False")

        self._tools[name] = tool
        logger.debug("Registered tool '%s' (%s)", name, type(tool).__name__)

    def unregister(self, name: str) -> None:
        """Remove a tool. No error if missing."""
        if name in self._tools:
            self._tools.pop(name, None)
            logger.debug("Unregistered tool '%s'", name)

    def get(self, name: str) -> Any:
        """Return the tool object or raise UnknownToolError."""
        try:
            return self._tools[name]
        except KeyError as e:
            raise UnknownToolError(f"Unknown tool: {name}") from e

    def has(self, name: str) -> bool:
        """Return True if a tool is registered."""
        return name in self._tools

    def list(self) -> List[str]:
        """List registered tool names (sorted)."""
        return sorted(self._tools.keys())

    # -- Invocation API --

    async def call(self, name: str, payload: Dict[str, Any], *, timeout: Optional[float] = None) -> Dict[str, Any]:
        """
        Invoke a tool by name with a dict payload. Returns a dict result.

        - Runs `before_hooks` and `after_hooks` around the call.
        - If the tool's `call` is sync, executes it inline (blocking).
          Prefer async tools in production for non-blocking behavior.
        - If `timeout` is provided, the call is wrapped by `asyncio.wait_for`
          for async tools; sync tools ignore `timeout`.

        Raises:
            UnknownToolError, InvalidToolError, asyncio.TimeoutError
        """
        tool = self.get(name)
        call_fn = getattr(tool, "call", None)
        if call_fn is None or not callable(call_fn):
            raise InvalidToolError(f"Tool '{name}' has no callable 'call' method")

        # Fire before hooks (best-effort)
        for hook in self.before_hooks:
            try:
                hook(name, payload)
            except Exception as e:  # pragma: no cover
                logger.debug("before_hook error for '%s': %s", name, e)

        result: Optional[Dict[str, Any]] = None
        error: Optional[BaseException] = None

        try:
            if inspect.iscoroutinefunction(call_fn):
                # Async tool
                if timeout is not None and timeout > 0:
                    result = await asyncio.wait_for(call_fn(payload), timeout=timeout)
                else:
                    result = await call_fn(payload)
            else:
                # Sync tool (discouraged in production)
                logger.debug("Calling sync tool '%s' (consider making it async)", name)
                out = call_fn(payload)
                # If the sync tool returned a coroutine by mistake, await it
                if inspect.isawaitable(out):
                    result = await out  # type: ignore[assignment]
                else:
                    result = out  # type: ignore[assignment]

            if not isinstance(result, dict):
                raise InvalidToolError(f"Tool '{name}' must return a dict, got {type(result).__name__}")

            return result

        except BaseException as e:
            error = e
            raise

        finally:
            # Fire after hooks (best-effort)
            for hook in self.after_hooks:
                try:
                    hook(name, payload, result, error)
                except Exception as e:  # pragma: no cover
                    logger.debug("after_hook error for '%s': %s", name, e)
