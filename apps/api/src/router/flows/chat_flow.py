"""
Chat Flow
Normal conversational chat flow
"""

from typing import Dict, Any, Optional
from .base_flow import BaseFlow


class ChatFlow(BaseFlow):
    """Simple conversational chat flow"""
    
    async def execute(
        self,
        message: str,
        session_id: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute normal chat flow
        
        Args:
            message: User message
            session_id: Session identifier
            context: Optional context
            
        Returns:
            Chat response
        """
        # Load conversation history from memory
        memory = await self._load_memory(session_id)
        conversation_history = memory.get("history", [])
        
        # Add user message to history
        conversation_history.append({
            "role": "user",
            "content": message
        })
        
        # Generate response using LLM
        response = await self._generate_response(conversation_history)
        
        # Add assistant response to history
        conversation_history.append({
            "role": "assistant",
            "content": response
        })
        
        # Save updated memory
        memory["history"] = conversation_history[-10:]  # Keep last 10 messages
        await self._save_memory(session_id, memory)
        
        return {
            "response": response,
            "type": "chat",
            "metadata": {
                "turn_count": len(conversation_history) // 2
            }
        }
    
    async def _generate_response(self, conversation_history: list) -> str:
        """Generate response using LLM"""
        # TODO: Implement actual LLM call
        # This is a placeholder
        
        messages = conversation_history
        
        # Call LLM (placeholder)
        # response = await self.llm_client.generate(messages)
        
        # For now, return a simple response
        return "I'm here to help! This is a normal chat response."

