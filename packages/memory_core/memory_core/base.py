# packages/memory_core/memory_core/base.py
"""
Memory interface for agent state persistence and retrieval.
"""
from __future__ import annotations

from typing import Protocol, Any, Dict, List, Optional


class IMemory(Protocol):
    """Protocol defining the memory interface for agent systems."""
    
    async def save(self, session_id: str, key: str, value: Any) -> None:
        """Save a value to memory."""
        ...
    
    async def get(self, session_id: str, key: str, default: Any = None) -> Any:
        """Retrieve a value from memory."""
        ...
    
    async def delete(self, session_id: str, key: str) -> None:
        """Delete a value from memory."""
        ...
    
    async def get_history(self, session_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get conversation history for a session."""
        ...
    
    async def clear_session(self, session_id: str) -> None:
        """Clear all memory for a session."""
        ...

