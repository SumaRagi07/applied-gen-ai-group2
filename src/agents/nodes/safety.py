import json
import os
import time
from pathlib import Path
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from ..prompts import SAFETY_PROMPT
from ..utils.logger import get_logger

# Load .env from project root
project_root = Path(__file__).parent.parent.parent.parent
env_path = project_root / ".env"
load_dotenv(dotenv_path=env_path, override=True)

def safety_node(state):
    """Check if query is safe and appropriate"""
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
    
    prompt = SAFETY_PROMPT.format(query=state['user_query'])
    
    response = llm.invoke([
        SystemMessage(content="You are a content safety checker."),
        HumanMessage(content=prompt)
    ])
    
    # Parse JSON response
    try:
        safety_check = json.loads(response.content)
    except json.JSONDecodeError:
        # Default to safe if parsing fails
        safety_check = {"is_safe": True, "reason": None}
    
    is_safe = safety_check.get('is_safe', True)
    reason = safety_check.get('reason', None)
    
    output_data = {
        "is_safe": is_safe,
        "safety_reason": reason
    }
    duration_ms = (time.time() - start_time) * 1000
    
    # Log step
    logger.log_step(
        node_name="safety",
        input_data=input_data,
        output_data=output_data,
        duration_ms=duration_ms,
        metadata={
            "model": "gpt-4o",
            "safety_check_result": safety_check
        }
    )
    
    print(f"\n[SAFETY] Is safe: {is_safe}")
    if not is_safe:
        print(f"[SAFETY] Reason: {reason}")
    
    return output_data