"""
Safety Policy
Enforces safety constraints on agent execution
"""

from typing import Dict, Any, Optional, List, Set
from .base_policy import BasePolicy, PolicyViolation, PolicyViolationType


class SafetyPolicy(BasePolicy):
    """
    Enforces safety constraints including:
    - Content filtering
    - Rate limiting
    - Timeout enforcement
    - Resource limits
    - Allowed tools
    """
    
    def __init__(
        self,
        content_filters: Optional[List[str]] = None,
        blocked_keywords: Optional[Set[str]] = None,
        rate_limit_per_minute: Optional[int] = None,
        max_timeout_seconds: int = 600,
        max_memory_mb: Optional[int] = None,
        allowed_tools: Optional[List[str]] = None,
        blocked_tools: Optional[List[str]] = None
    ):
        """
        Initialize Safety Policy
        
        Args:
            content_filters: List of content filter categories to apply
            blocked_keywords: Set of blocked keywords
            rate_limit_per_minute: Maximum requests per minute
            max_timeout_seconds: Maximum execution time
            max_memory_mb: Maximum memory usage in MB
            allowed_tools: Whitelist of allowed tools
            blocked_tools: Blacklist of blocked tools
        """
        self.content_filters = content_filters or []
        self.blocked_keywords = blocked_keywords or set()
        self.rate_limit_per_minute = rate_limit_per_minute
        self.max_timeout_seconds = max_timeout_seconds
        self.max_memory_mb = max_memory_mb
        self.allowed_tools = set(allowed_tools) if allowed_tools else None
        self.blocked_tools = set(blocked_tools) if blocked_tools else set()
        
        # Rate limiting state (in production, use Redis)
        self._request_counts: Dict[str, List[float]] = {}
    
    def validate(self, context: Dict[str, Any]) -> tuple[bool, Optional[PolicyViolation]]:
        """Validate context against safety policy"""
        
        # Check content filters
        violation = self._check_content(context)
        if violation:
            return False, violation
        
        # Check rate limits
        violation = self._check_rate_limit(context)
        if violation:
            return False, violation
        
        # Check timeout
        violation = self._check_timeout(context)
        if violation:
            return False, violation
        
        # Check tool usage
        violation = self._check_tools(context)
        if violation:
            return False, violation
        
        return True, None
    
    def enforce(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Enforce safety constraints"""
        modified = context.copy()
        
        # Enforce timeout
        if "timeout_seconds" in modified:
            modified["timeout_seconds"] = min(
                modified["timeout_seconds"],
                self.max_timeout_seconds
            )
        
        # Filter tools
        if "requested_tools" in modified:
            modified["requested_tools"] = self._filter_tools(
                modified["requested_tools"]
            )
        
        # Add safety metadata
        modified["safety_policy_applied"] = True
        modified["content_filters"] = self.content_filters
        
        return modified
    
    def _check_content(self, context: Dict[str, Any]) -> Optional[PolicyViolation]:
        """Check for content violations"""
        query = context.get("query", "").lower()
        
        # Check blocked keywords
        for keyword in self.blocked_keywords:
            if keyword.lower() in query:
                return PolicyViolation(
                    violation_type=PolicyViolationType.CONTENT,
                    message=f"Query contains blocked keyword: {keyword}",
                    severity="error",
                    details={"keyword": keyword}
                )
        
        # Check content filters (placeholder - would integrate with actual content moderation)
        for filter_category in self.content_filters:
            if self._matches_filter(query, filter_category):
                return PolicyViolation(
                    violation_type=PolicyViolationType.CONTENT,
                    message=f"Query matches content filter: {filter_category}",
                    severity="error",
                    details={"filter": filter_category}
                )
        
        return None
    
    def _matches_filter(self, text: str, filter_category: str) -> bool:
        """Check if text matches filter category"""
        # Placeholder - would integrate with content moderation API
        filter_keywords = {
            "adult": ["porn", "xxx", "sex", "adult"],
            "illegal": ["drug", "weapon", "illegal", "hack"],
            "harmful": ["suicide", "self-harm", "violence"],
        }
        
        keywords = filter_keywords.get(filter_category, [])
        return any(kw in text.lower() for kw in keywords)
    
    def _check_rate_limit(self, context: Dict[str, Any]) -> Optional[PolicyViolation]:
        """Check rate limits"""
        if not self.rate_limit_per_minute:
            return None
        
        user_id = context.get("user_id", "anonymous")
        current_time = context.get("timestamp", 0)
        
        # Get request history for user
        if user_id not in self._request_counts:
            self._request_counts[user_id] = []
        
        # Remove old requests (older than 1 minute)
        cutoff_time = current_time - 60
        self._request_counts[user_id] = [
            t for t in self._request_counts[user_id] if t > cutoff_time
        ]
        
        # Check if over limit
        if len(self._request_counts[user_id]) >= self.rate_limit_per_minute:
            return PolicyViolation(
                violation_type=PolicyViolationType.RATE_LIMIT,
                message=f"Rate limit exceeded: {self.rate_limit_per_minute} per minute",
                severity="error",
                details={
                    "limit": self.rate_limit_per_minute,
                    "current": len(self._request_counts[user_id])
                }
            )
        
        # Add current request
        self._request_counts[user_id].append(current_time)
        
        return None
    
    def _check_timeout(self, context: Dict[str, Any]) -> Optional[PolicyViolation]:
        """Check timeout constraints"""
        requested_timeout = context.get("timeout_seconds", 0)
        
        if requested_timeout > self.max_timeout_seconds:
            return PolicyViolation(
                violation_type=PolicyViolationType.TIMEOUT,
                message=f"Requested timeout {requested_timeout}s exceeds maximum {self.max_timeout_seconds}s",
                severity="warning",
                details={
                    "requested": requested_timeout,
                    "maximum": self.max_timeout_seconds
                }
            )
        
        return None
    
    def _check_tools(self, context: Dict[str, Any]) -> Optional[PolicyViolation]:
        """Check tool usage constraints"""
        requested_tools = context.get("requested_tools", [])
        
        for tool in requested_tools:
            # Check if tool is blocked
            if tool in self.blocked_tools:
                return PolicyViolation(
                    violation_type=PolicyViolationType.SAFETY,
                    message=f"Tool '{tool}' is blocked by policy",
                    severity="error",
                    details={"tool": tool}
                )
            
            # Check if tool is in allowlist (if allowlist exists)
            if self.allowed_tools and tool not in self.allowed_tools:
                return PolicyViolation(
                    violation_type=PolicyViolationType.SAFETY,
                    message=f"Tool '{tool}' is not in allowed tools list",
                    severity="error",
                    details={"tool": tool, "allowed": list(self.allowed_tools)}
                )
        
        return None
    
    def _filter_tools(self, tools: List[str]) -> List[str]:
        """Filter tools based on policy"""
        filtered = []
        
        for tool in tools:
            # Skip blocked tools
            if tool in self.blocked_tools:
                continue
            
            # If allowlist exists, only include allowed tools
            if self.allowed_tools and tool not in self.allowed_tools:
                continue
            
            filtered.append(tool)
        
        return filtered

