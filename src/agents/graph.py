from langgraph.graph import StateGraph, END
from .state import State
from .nodes.router import router_node
from .nodes.safety import safety_node
from .nodes.planner import planner_node
from .nodes.executor import executor_node
from .nodes.synthesizer import synthesizer_node

def create_graph():
    """Assemble the LangGraph workflow"""
    
    # Create graph
    workflow = StateGraph(State)
    
    # Add nodes
    workflow.add_node("router", router_node)
    workflow.add_node("safety", safety_node)
    workflow.add_node("planner", planner_node)
    workflow.add_node("executor", executor_node)
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
    workflow.add_edge("executor", "synthesizer")
    workflow.add_edge("synthesizer", END)
    
    # Compile
    app = workflow.compile()
    
    return app

# Create the app
agent_graph = create_graph()