"""
Base Profile
Abstract base class for agent profiles
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class AgentConfig:
    """Configuration for an agent"""
    
    # Identity
    agent_type: str
    agent_name: str
    description: str
    
    # System Prompt
    system_prompt: str
    
    # Tool Configuration
    allowed_tools: List[str]  # Tool names that can be used
    required_tools: List[str] = field(default_factory=list)  # Must be available
    
    # Execution Limits
    max_steps: int = 10  # Maximum Plan-Act loop iterations
    max_depth: int = 5   # Maximum recursive depth
    max_tokens: int = 100000  # Token budget
    timeout_seconds: int = 300  # 5 minutes default
    
    # Performance Targets
    target_latency_ms: int = 5000  # Target response time
    allow_parallel_tools: bool = True  # Execute tools in parallel
    
    # Memory Configuration
    use_memory: bool = True
    memory_window: int = 10  # Number of previous interactions to keep
    
    # Quality Controls
    min_confidence: float = 0.7  # Minimum confidence to proceed
    require_sources: bool = False  # Require source citations
    enable_reflection: bool = True  # Enable reflection phase
    
    # Cost Controls
    max_cost_usd: Optional[float] = None  # Maximum cost per request
    use_cache: bool = True  # Use cached results when available
    
    # Safety
    content_filters: List[str] = field(default_factory=list)
    rate_limit_per_minute: Optional[int] = None
    
    # Custom Parameters
    custom_params: Dict[str, Any] = field(default_factory=dict)


class BaseProfile(ABC):
    """Abstract base class for agent profiles"""
    
    @abstractmethod
    def get_config(self) -> AgentConfig:
        """Get agent configuration"""
        pass
    
    @abstractmethod
    def get_system_prompt(self) -> str:
        """Get system prompt for this agent"""
        pass
    
    @abstractmethod
    def get_allowed_tools(self) -> List[str]:
        """Get list of allowed tool names"""
        pass
    
    def validate_config(self, config: AgentConfig) -> bool:
        """Validate configuration"""
        if config.max_steps <= 0:
            raise ValueError("max_steps must be positive")
        
        if config.max_tokens <= 0:
            raise ValueError("max_tokens must be positive")
        
        if not (0.0 <= config.min_confidence <= 1.0):
            raise ValueError("min_confidence must be between 0 and 1")
        
        return True
    
    def apply_policy(self, config: AgentConfig, policy: Any) -> AgentConfig:
        """Apply policy constraints to configuration"""
        # Will be implemented when policies are integrated
        return config

