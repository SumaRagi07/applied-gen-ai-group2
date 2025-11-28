from langgraph.graph import StateGraph, END
from .state import State
from .nodes.router import router_node
from .nodes.safety import safety_node
from .nodes.planner import planner_node
from .nodes.executor import executor_node
from .nodes.reconciler import reconciler_node
from .nodes.synthesizer import synthesizer_node
from .utils.logger import get_logger

def create_graph():
    """Assemble the LangGraph workflow"""
    
    # Create graph
    workflow = StateGraph(State)
    
    # Add nodes
    workflow.add_node("router", router_node)
    workflow.add_node("safety", safety_node)
    workflow.add_node("planner", planner_node)
    workflow.add_node("executor", executor_node)
    workflow.add_node("reconciler", reconciler_node)
    workflow.add_node("synthesizer", synthesizer_node)
    
    # Define flow
    workflow.set_entry_point("router")
    workflow.add_edge("router", "safety")
    
    # Conditional: only continue if safe
    def check_safety(state):
        if state.get('is_safe', True):
            return "planner"
        else:
            return "synthesizer"  # Go to synthesizer to return error message
    
    workflow.add_conditional_edges(
        "safety",
        check_safety
    )
    
    workflow.add_edge("planner", "executor")
    workflow.add_edge("executor", "reconciler")
    workflow.add_edge("reconciler", "synthesizer")
    workflow.add_edge("synthesizer", END)
    
    # Compile
    app = workflow.compile()
    
    return app

def invoke_with_logging(query: str):
    """Invoke agent graph with logging"""
    logger = get_logger()
    session_id = logger.start_session(query)
    
    try:
        result = agent_graph.invoke({"user_query": query})
        
        # End session and save log
        log_file = logger.end_session()
        
        # Add logging metadata to result
        result['_logging'] = {
            'session_id': session_id,
            'log_file': str(log_file),
            'step_summary': logger.get_step_summary(),
            'execution_stats': logger.get_execution_stats()
        }
        
        return result
    except Exception as e:
        # Log error before ending session
        logger.end_session()
        raise

# Create the app
agent_graph = create_graph()