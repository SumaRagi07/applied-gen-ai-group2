from typing import TypedDict, Optional, List, Dict, Any

class State(TypedDict):
    """State that flows through all LangGraph nodes"""
    
    # User input
    user_query: str
    
    # Router output
    intent: Optional[Dict[str, Any]]
    
    # Safety output
    is_safe: Optional[bool]
    safety_reason: Optional[str]
    
    # Planner output
    plan: Optional[str]
    tools_to_call: Optional[List[str]]
    rag_params: Optional[Dict[str, Any]]
    
    # Executor output
    rag_results: Optional[List[Dict]]
    web_results: Optional[List[Dict]]
    
    # Synthesizer output
    final_answer: Optional[str]
    citations: Optional[List[str]]