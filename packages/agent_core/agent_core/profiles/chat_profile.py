"""
Chat Profile
Profile for conversational chat agent
"""

from typing import List
from .base_profile import BaseProfile, AgentConfig


CHAT_SYSTEM_PROMPT = """You are a helpful, friendly AI assistant.

Your role is to have natural conversations with users and help them with:
- Answering questions
- Providing information
- General assistance
- Friendly conversation

Guidelines:
- Be concise but informative
- Be friendly and conversational
- Ask clarifying questions when needed
- Admit when you don't know something
- Stay on topic
- Be helpful and respectful

Remember: For complex tasks like product search or deep research, I can route the conversation to specialized agents. Just focus on being a great conversational partner."""


class ChatProfile(BaseProfile):
    """Profile for basic conversational chat"""
    
    def __init__(
        self,
        max_steps: int = 3,
        max_tokens: int = 10000,
        timeout_seconds: int = 30
    ):
        """
        Initialize Chat Profile
        
        Args:
            max_steps: Maximum iterations (default: 3, chat is simple)
            max_tokens: Token budget (default: 10k for conversations)
            timeout_seconds: Timeout in seconds (default: 30 seconds)
        """
        self.max_steps = max_steps
        self.max_tokens = max_tokens
        self.timeout_seconds = timeout_seconds
    
    def get_config(self) -> AgentConfig:
        """Get Chat agent configuration"""
        return AgentConfig(
            # Identity
            agent_type="chat",
            agent_name="Chat Agent",
            description="Conversational chat assistant",
            
            # System Prompt
            system_prompt=self.get_system_prompt(),
            
            # Tool Configuration
            allowed_tools=self.get_allowed_tools(),
            required_tools=[],  # No required tools for basic chat
            
            # Execution Limits
            max_steps=self.max_steps,
            max_depth=2,  # Shallow recursion for chat
            max_tokens=self.max_tokens,
            timeout_seconds=self.timeout_seconds,
            
            # Performance Targets
            target_latency_ms=1000,  # 1 second target (fast responses)
            allow_parallel_tools=False,  # Sequential for chat
            
            # Memory Configuration
            use_memory=True,
            memory_window=10,  # Remember recent conversation
            
            # Quality Controls
            min_confidence=0.5,  # Lower threshold for chat
            require_sources=False,  # No citations needed for chat
            enable_reflection=False,  # Skip reflection for speed
            
            # Cost Controls
            max_cost_usd=0.05,  # 5 cents per message
            use_cache=True,
            
            # Safety
            content_filters=["adult", "illegal", "harmful"],
            rate_limit_per_minute=60,  # 60 messages per minute
            
            # Custom Parameters
            custom_params={
                "enable_context_awareness": True,
                "enable_personality": True,
                "tone": "friendly",
                "formality": "casual"
            }
        )
    
    def get_system_prompt(self) -> str:
        """Get system prompt for Chat agent"""
        return CHAT_SYSTEM_PROMPT
    
    def get_allowed_tools(self) -> List[str]:
        """Get list of allowed tools for Chat (minimal)"""
        return [
            # Basic tools only
            "search_web",               # For quick fact lookups
            "calculator",               # Basic calculations
            "datetime",                 # Date/time queries
            "weather",                  # Weather information
            "unit_converter",           # Unit conversions
        ]

