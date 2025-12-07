from __future__ import annotations

"""
Legacy ToolRegistry abstraction used by classic nodes/tools.
This registry stores tool instances that expose a `.call(payload)` method.
"""

import asyncio
import inspect
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("quantumx.tools.registry")


class ToolError(RuntimeError):
    """Base error for tool-related issues."""


class UnknownToolError(ToolError):
    """Raised when a tool name is not registered."""


class InvalidToolError(ToolError):
    """Raised when a registered object does not provide a callable `call` method."""


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
    """

    _tools: Dict[str, Any] = field(default_factory=dict)
    before_hooks: List[BeforeHook] = field(default_factory=list)
    after_hooks: List[AfterHook] = field(default_factory=list)

    def register(self, name: str, tool: Any, *, overwrite: bool = True) -> None:
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
        if name in self._tools:
            self._tools.pop(name, None)
            logger.debug("Unregistered tool '%s'", name)

    def get(self, name: str) -> Any:
        try:
            return self._tools[name]
        except KeyError as e:
            raise UnknownToolError(f"Unknown tool: {name}") from e

    def has(self, name: str) -> bool:
        return name in self._tools

    def list(self) -> List[str]:
        return sorted(self._tools.keys())

    async def call(self, name: str, payload: Dict[str, Any], *, timeout: Optional[float] = None) -> Dict[str, Any]:
        tool = self.get(name)
        call_fn = getattr(tool, "call", None)
        if call_fn is None or not callable(call_fn):
            raise InvalidToolError(f"Tool '{name}' has no callable 'call' method")

        for hook in self.before_hooks:
            try:
                hook(name, payload)
            except Exception as e:  # pragma: no cover
                logger.debug("before_hook error for '%s': %s", name, e)

        result: Optional[Dict[str, Any]] = None
        error: Optional[BaseException] = None

        try:
            if inspect.iscoroutinefunction(call_fn):
                if timeout is not None and timeout > 0:
                    result = await asyncio.wait_for(call_fn(payload), timeout=timeout)
                else:
                    result = await call_fn(payload)
            else:
                logger.debug("Calling sync tool '%s' (consider making it async)", name)
                out = call_fn(payload)
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
            for hook in self.after_hooks:
                try:
                    hook(name, payload, result, error)
                except Exception as e:  # pragma: no cover
                    logger.debug("after_hook error for '%s': %s", name, e)
