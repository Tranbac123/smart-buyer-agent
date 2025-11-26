"""
Deep Research Profile
Profile for Deep Research Agent - In-depth analysis and research
"""

from typing import List
from .base_profile import BaseProfile, AgentConfig


DEEP_RESEARCH_SYSTEM_PROMPT = """You are a Deep Research Agent - an expert research assistant that conducts thorough, multi-step investigations to answer complex questions.

Your Capabilities:
1. **Strategic Planning**: Break down complex questions into manageable research steps
2. **Multi-Source Research**: Search web, academic sources, documents, and databases
3. **Critical Analysis**: Evaluate source credibility and information quality
4. **Synthesis**: Combine information from multiple sources into coherent insights
5. **Iterative Refinement**: Continuously improve understanding through reflection
6. **Comprehensive Reporting**: Provide detailed, well-cited answers

Your Approach:
- **Plan Thoroughly**: Create a research strategy before executing
- **Search Widely**: Use multiple search strategies and sources
- **Think Critically**: Evaluate evidence and identify gaps
- **Reflect Often**: Assess progress and adjust strategy
- **Cite Sources**: Always provide references for claims
- **Synthesize Well**: Connect insights into a coherent narrative

Research Process (Plan → Act → Observe → Reflect → Refine):
1. **Plan**: Decompose question, identify key topics, plan search strategy
2. **Act**: Execute searches, retrieve documents, query databases
3. **Observe**: Extract key information, assess quality, identify patterns
4. **Reflect**: Evaluate completeness, identify gaps, assess confidence
5. **Refine**: Adjust strategy, conduct follow-up searches if needed
6. **Finalize**: Synthesize findings into comprehensive answer

Quality Standards:
- Cite all sources with URLs/references
- Acknowledge uncertainty and limitations
- Present multiple perspectives when relevant
- Distinguish facts from interpretations
- Provide confidence levels for conclusions

Remember: Your goal is DEPTH and ACCURACY, not speed."""


class DeepResearchProfile(BaseProfile):
    """Profile for Deep Research Agent"""
    
    def __init__(
        self,
        max_steps: int = 15,
        max_tokens: int = 200000,
        timeout_seconds: int = 600
    ):
        """
        Initialize Deep Research Profile
        
        Args:
            max_steps: Maximum Plan-Act loop iterations (default: 15)
            max_tokens: Token budget (default: 200k for thorough research)
            timeout_seconds: Timeout in seconds (default: 10 minutes)
        """
        self.max_steps = max_steps
        self.max_tokens = max_tokens
        self.timeout_seconds = timeout_seconds
    
    def get_config(self) -> AgentConfig:
        """Get Deep Research agent configuration"""
        return AgentConfig(
            # Identity
            agent_type="deep_research",
            agent_name="Deep Research Agent",
            description="In-depth research and analysis agent",
            
            # System Prompt
            system_prompt=self.get_system_prompt(),
            
            # Tool Configuration
            allowed_tools=self.get_allowed_tools(),
            required_tools=["search_web", "summarize_doc"],
            
            # Execution Limits
            max_steps=self.max_steps,
            max_depth=7,  # Allow deeper recursion for complex research
            max_tokens=self.max_tokens,
            timeout_seconds=self.timeout_seconds,
            
            # Performance Targets
            target_latency_ms=30000,  # 30 seconds target (research takes time)
            allow_parallel_tools=True,  # Search multiple sources in parallel
            
            # Memory Configuration
            use_memory=True,
            memory_window=20,  # Remember more context for research
            
            # Quality Controls
            min_confidence=0.8,  # High confidence required
            require_sources=True,  # Always cite sources
            enable_reflection=True,  # Critical for research quality
            
            # Cost Controls
            max_cost_usd=2.00,  # $2 per research query (higher for thorough work)
            use_cache=True,
            
            # Safety
            content_filters=["illegal"],
            rate_limit_per_minute=5,  # Fewer but deeper queries
            
            # Custom Parameters
            custom_params={
                "min_sources": 3,
                "max_sources": 10,
                "require_diverse_sources": True,
                "enable_academic_search": True,
                "enable_fact_checking": True,
                "citation_style": "apa",
                "confidence_threshold": 0.8,
                "enable_multi_perspective": True
            }
        )
    
    def get_system_prompt(self) -> str:
        """Get system prompt for Deep Research agent"""
        return DEEP_RESEARCH_SYSTEM_PROMPT
    
    def get_allowed_tools(self) -> List[str]:
        """Get list of allowed tools for Deep Research"""
        return [
            # Core research tools
            "search_web",               # Web search
            "search_academic",          # Academic paper search
            "search_news",              # News search
            "summarize_doc",            # Document summarization
            "extract_content",          # Extract content from URLs
            
            # Analysis tools
            "fact_checker",             # Verify facts
            "source_evaluator",         # Evaluate source credibility
            "citation_generator",       # Generate citations
            "sentiment_analyzer",       # Analyze sentiment
            
            # Database tools
            "query_db",                 # Query databases
            "knowledge_graph",          # Query knowledge graphs
            
            # RAG tools
            "rag_retriever",            # Retrieve from knowledge base
            "rag_indexer",              # Index documents
            
            # Synthesis tools
            "outline_generator",        # Generate research outlines
            "report_formatter",         # Format final reports
            "visualization",            # Create charts/graphs
        ]

