"""
Base Policy
Abstract base class for agent policies
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional, Dict
from enum import Enum


class PolicyViolationType(Enum):
    """Types of policy violations"""
    SAFETY = "safety"
    COST = "cost"
    RATE_LIMIT = "rate_limit"
    CONTENT = "content"
    TIMEOUT = "timeout"
    RESOURCE = "resource"


@dataclass
class PolicyViolation:
    """Represents a policy violation"""
    violation_type: PolicyViolationType
    message: str
    severity: str  # "warning", "error", "critical"
    details: Optional[Dict[str, Any]] = None
    
    def __str__(self) -> str:
        return f"[{self.severity.upper()}] {self.violation_type.value}: {self.message}"


class BasePolicy(ABC):
    """Abstract base class for policies"""
    
    @abstractmethod
    def validate(self, context: Dict[str, Any]) -> tuple[bool, Optional[PolicyViolation]]:
        """
        Validate against policy
        
        Args:
            context: Execution context to validate
            
        Returns:
            Tuple of (is_valid, violation_if_any)
        """
        pass
    
    @abstractmethod
    def enforce(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enforce policy constraints on context
        
        Args:
            context: Execution context
            
        Returns:
            Modified context with policy constraints applied
        """
        pass
    
    def get_name(self) -> str:
        """Get policy name"""
        return self.__class__.__name__

