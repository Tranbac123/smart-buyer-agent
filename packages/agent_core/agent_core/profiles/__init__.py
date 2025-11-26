"""
Agent Profiles
Configuration profiles for different agent types
"""

from .base_profile import BaseProfile, AgentConfig
from .smart_buyer_profile import SmartBuyerProfile
from .deep_research_profile import DeepResearchProfile
from .chat_profile import ChatProfile

__all__ = [
    "BaseProfile",
    "AgentConfig",
    "SmartBuyerProfile",
    "DeepResearchProfile",
    "ChatProfile",
]

