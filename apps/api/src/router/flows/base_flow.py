"""
Base Flow
Abstract base class for all flows
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class BaseFlow(ABC):
    """Abstract base class for agent flows"""
    
    def __init__(self, llm_client: Any, memory_service: Any):
        """
        Initialize base flow
        
        Args:
            llm_client: LLM client for inference
            memory_service: Memory service for context
        """
        self.llm_client = llm_client
        self.memory_service = memory_service
    
    @abstractmethod
    async def execute(
        self,
        message: str,
        session_id: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute the flow
        
        Args:
            message: User message
            session_id: Session identifier
            context: Optional context information
            
        Returns:
            Flow execution result
        """
        pass
    
    async def _load_memory(self, session_id: str) -> Dict[str, Any]:
        """Load memory for the session"""
        # TODO: Implement memory loading
        return {}
    
    async def _save_memory(
        self,
        session_id: str,
        memory: Dict[str, Any]
    ) -> None:
        """Save memory for the session"""
        # TODO: Implement memory saving
        pass

