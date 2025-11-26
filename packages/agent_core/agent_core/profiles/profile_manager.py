"""
Profile Manager
Manages agent profiles and applies policies
"""

from typing import Dict, Any, Optional, List
from .base_profile import BaseProfile, AgentConfig
from .smart_buyer_profile import SmartBuyerProfile
from .deep_research_profile import DeepResearchProfile
from .chat_profile import ChatProfile
from ..policy.base_policy import BasePolicy, PolicyViolation
from ..policy.safety_policy import SafetyPolicy
from ..policy.cost_policy import CostPolicy


class ProfileManager:
    """Manages agent profiles and policy enforcement"""
    
    def __init__(self):
        """Initialize profile manager"""
        self._profiles: Dict[str, BaseProfile] = {
            "smart_buyer": SmartBuyerProfile(),
            "deep_research": DeepResearchProfile(),
            "chat": ChatProfile(),
        }
        
        self._policies: List[BasePolicy] = []
    
    def register_profile(self, agent_type: str, profile: BaseProfile):
        """Register a new profile"""
        self._profiles[agent_type] = profile
    
    def get_profile(self, agent_type: str) -> Optional[BaseProfile]:
        """Get profile by agent type"""
        return self._profiles.get(agent_type)
    
    def get_config(
        self,
        agent_type: str,
        apply_policies: bool = True
    ) -> Optional[AgentConfig]:
        """
        Get configuration for agent type
        
        Args:
            agent_type: Type of agent (smart_buyer, deep_research, chat)
            apply_policies: Whether to apply registered policies
            
        Returns:
            Agent configuration with policies applied
        """
        profile = self.get_profile(agent_type)
        if not profile:
            return None
        
        config = profile.get_config()
        
        # Apply policies if requested
        if apply_policies:
            config = self._apply_policies(config)
        
        return config
    
    def add_policy(self, policy: BasePolicy):
        """Add a policy to be applied to all profiles"""
        self._policies.append(policy)
    
    def _apply_policies(self, config: AgentConfig) -> AgentConfig:
        """Apply all registered policies to configuration"""
        # For now, just add safety and cost policies based on config
        # In production, this would enforce actual policy constraints
        return config
    
    def validate_execution(
        self,
        agent_type: str,
        context: Dict[str, Any]
    ) -> tuple[bool, List[PolicyViolation]]:
        """
        Validate execution against all policies
        
        Args:
            agent_type: Type of agent
            context: Execution context
            
        Returns:
            Tuple of (is_valid, list_of_violations)
        """
        violations = []
        
        # Get profile config
        config = self.get_config(agent_type, apply_policies=False)
        if not config:
            violations.append(PolicyViolation(
                violation_type="error",
                message=f"Unknown agent type: {agent_type}",
                severity="error"
            ))
            return False, violations
        
        # Create policies from config
        policies = self._create_policies_from_config(config)
        
        # Validate against each policy
        for policy in policies:
            is_valid, violation = policy.validate(context)
            if not is_valid and violation:
                violations.append(violation)
        
        return len(violations) == 0, violations
    
    def _create_policies_from_config(self, config: AgentConfig) -> List[BasePolicy]:
        """Create policy instances from configuration"""
        policies = []
        
        # Safety policy
        safety_policy = SafetyPolicy(
            content_filters=config.content_filters,
            rate_limit_per_minute=config.rate_limit_per_minute,
            max_timeout_seconds=config.timeout_seconds,
            allowed_tools=config.allowed_tools
        )
        policies.append(safety_policy)
        
        # Cost policy
        if config.max_cost_usd:
            cost_policy = CostPolicy(
                max_cost_per_request=config.max_cost_usd,
                max_tokens_per_request=config.max_tokens,
                enable_caching=config.use_cache
            )
            policies.append(cost_policy)
        
        return policies


# Singleton instance
_profile_manager = ProfileManager()


def get_profile_manager() -> ProfileManager:
    """Get global profile manager instance"""
    return _profile_manager

