"""
Router Service
Entry point for routing requests to appropriate flows/agents
"""

from typing import Dict, Any, Optional, Union
from enum import Enum

from router.flows.base_flow import BaseFlow
from router.flows.chat_flow import ChatFlow
from router.flows.deep_research_flow import DeepResearchFlow
from router.flows.smart_buyer_flow import SmartBuyerFlow
from router.flows.code_agent_flow import CodeAgentFlow


class Intent(Enum):
    """User intent types"""
    CHAT = "chat"
    SMART_BUYER = "smart_buyer"
    DEEP_RESEARCH = "deep_research"
    CODE_AGENT = "code_agent"


class FlowType(Enum):
    """Types of available flows"""
    CHAT = "chat"
    DEEP_RESEARCH = "deep_research"
    SMART_BUYER = "smart_buyer"
    CODE_AGENT = "code_agent"


class RouterService:
    """Routes requests to appropriate flow based on intent and context"""
    
    def __init__(
        self,
        llm_client: Any,
        memory_service: Any,
        tools_registry: Any,
        rag_service: Any
    ):
        """
        Initialize router with dependencies
        
        Args:
            llm_client: LLM client for inference
            memory_service: Memory service for context
            tools_registry: Registry of available tools
            rag_service: RAG service for retrieval
        """
        self.llm_client = llm_client
        self.memory_service = memory_service
        self.tools_registry = tools_registry
        self.rag_service = rag_service
        
        # Initialize flows (lazy initialization via select_flow)
        self._flow_cache: Dict[Intent, BaseFlow] = {}
    
    def select_flow(self, user_intent: Intent) -> BaseFlow:
        """
        Select and return the appropriate flow based on user intent
        
        Args:
            user_intent: The detected user intent
            
        Returns:
            Flow instance for the given intent
            
        Example:
            >>> intent = Intent.SMART_BUYER
            >>> flow = router.select_flow(intent)
            >>> # Returns SmartBuyerFlow instance
        """
        # Check cache first
        if user_intent in self._flow_cache:
            return self._flow_cache[user_intent]
        
        # Create flow based on intent
        if user_intent == Intent.SMART_BUYER:
            flow = SmartBuyerFlow(
                self.llm_client,
                self.memory_service,
                self.tools_registry
            )
        elif user_intent == Intent.DEEP_RESEARCH:
            flow = DeepResearchFlow(
                self.llm_client,
                self.memory_service,
                self.tools_registry,
                self.rag_service
            )
        elif user_intent == Intent.CODE_AGENT:
            flow = CodeAgentFlow(
                self.llm_client,
                self.memory_service,
                self.tools_registry
            )
        else:  # Intent.CHAT or default
            flow = ChatFlow(
                self.llm_client,
                self.memory_service
            )
        
        # Cache the flow
        self._flow_cache[user_intent] = flow
        
        return flow
    
    async def route(
        self,
        message: str,
        session_id: str,
        context: Optional[Dict[str, Any]] = None,
        intent: Optional[Intent] = None
    ) -> Dict[str, Any]:
        """
        Route a message to the appropriate flow
        
        Args:
            message: User message
            session_id: Session identifier
            context: Optional context information
            intent: Optional explicit intent (if None, will auto-detect)
            
        Returns:
            Response from the selected flow
        """
        # Auto-detect intent if not specified
        if intent is None:
            intent = await self._detect_intent(message, context)
        
        # Select the appropriate flow based on intent
        flow = self.select_flow(intent)
        
        # Execute the flow
        response = await flow.execute(message, session_id, context)
        
        # Add metadata
        response["intent"] = intent.value
        response["flow_type"] = intent.value  # For backward compatibility
        response["session_id"] = session_id
        
        return response
    
    async def _detect_intent(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Intent:
        """
        Detect user intent based on message and context
        
        Args:
            message: User message
            context: Optional context
            
        Returns:
            Detected intent
        """
        message_lower = message.lower()
        
        # Check for smart buyer intent (e-commerce queries)
        # Smart-Buyer Search Agent becomes its own flow, not mixed with regular chat
        buyer_keywords = [
            "giá", "price", "mua", "buy", "so sánh", "compare",
            "rẻ nhất", "cheapest", "tốt nhất", "best deal",
            "shopee", "lazada", "tiki", "deal", "khuyến mãi", "discount",
            "sản phẩm", "product", "hàng", "goods"
        ]
        if any(keyword in message_lower for keyword in buyer_keywords):
            return Intent.SMART_BUYER
        
        # Check for deep research intent
        research_keywords = [
            "nghiên cứu", "research", "phân tích", "analyze", "tìm hiểu",
            "giải thích chi tiết", "explain in detail", "tổng hợp", "summarize",
            "so sánh chi tiết", "detailed comparison", "điều tra", "investigate"
        ]
        if any(keyword in message_lower for keyword in research_keywords):
            return Intent.DEEP_RESEARCH
        
        # Check for code agent intent
        code_keywords = [
            "code", "lập trình", "programming", "debug", "fix bug",
            "viết code", "write code", "refactor", "optimize code",
            "function", "class", "algorithm"
        ]
        if any(keyword in message_lower for keyword in code_keywords):
            return Intent.CODE_AGENT
        
        # Check context hints
        if context:
            explicit_intent = context.get("intent") or context.get("flow_type")
            if explicit_intent:
                try:
                    return Intent(explicit_intent)
                except ValueError:
                    pass
        
        # Default to chat flow
        return Intent.CHAT

