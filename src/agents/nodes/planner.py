import json
import os
import time
from pathlib import Path
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from ..prompts import PLANNER_PROMPT
from ..utils.logger import get_logger

# Load .env from project root
project_root = Path(__file__).parent.parent.parent.parent
env_path = project_root / ".env"
load_dotenv(dotenv_path=env_path, override=True)

def planner_node(state):
    """Decide which tools to call and with what parameters"""
    start_time = time.time()
    logger = get_logger()
    
    input_data = {
        "user_query": state.get('user_query', ''),
        "intent": state.get('intent', {})
    }
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or api_key.startswith("your_") or "placeholder" in api_key.lower():
        raise ValueError(f"Invalid OPENAI_API_KEY in .env file")
    
    llm = ChatOpenAI(
        model="gpt-4o", 
        temperature=0,
        api_key=api_key
    )
    
    prompt = PLANNER_PROMPT.format(
        query=state['user_query'],
        intent=json.dumps(state['intent'], indent=2)
    )
    
    response = llm.invoke([
        SystemMessage(content="You are a search strategy planner."),
        HumanMessage(content=prompt)
    ])
    
    # Parse JSON response
    try:
        plan = json.loads(response.content)
    except json.JSONDecodeError:
        # Fallback plan
        plan = {
            "plan": "Search catalog with basic query",
            "tools_to_call": ["rag.search"],
            "rag_params": {
                "query": state['user_query'],
                "top_k": 5
            }
        }
    
    output_data = {
        "plan": plan['plan'],
        "tools_to_call": plan['tools_to_call'],
        "rag_params": plan.get('rag_params', {})
    }
    duration_ms = (time.time() - start_time) * 1000
    
    # Log step
    logger.log_step(
        node_name="planner",
        input_data=input_data,
        output_data=output_data,
        duration_ms=duration_ms,
        metadata={
            "model": "gpt-4o",
            "planning_strategy": plan.get('plan', '')
        }
    )
    
    print(f"\n[PLANNER] Plan: {plan['plan']}")
    print(f"[PLANNER] Tools: {plan['tools_to_call']}")
    print(f"[PLANNER] RAG params: {plan.get('rag_params', {})}")
    
    return output_data