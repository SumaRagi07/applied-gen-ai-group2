import json
import os
import time
from pathlib import Path
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from ..prompts import ROUTER_PROMPT
from ..utils.logger import get_logger

# Load .env from project root (go up from src/agents/nodes/ to project root)
project_root = Path(__file__).parent.parent.parent.parent
env_path = project_root / ".env"
load_dotenv(dotenv_path=env_path, override=True)

def router_node(state):
    """Extract structured intent from user query"""
    start_time = time.time()
    logger = get_logger()
    
    input_data = {"user_query": state.get('user_query', '')}
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or api_key.startswith("your_") or "placeholder" in api_key.lower():
        raise ValueError(
            f"Invalid OPENAI_API_KEY. Please set a valid API key in .env file. "
            f"Current value: {api_key[:20] + '...' if api_key and len(api_key) > 20 else api_key}"
        )
    
    llm = ChatOpenAI(
        model="gpt-4o", 
        temperature=0,
        api_key=api_key
    )
    
    prompt = ROUTER_PROMPT.format(query=state['user_query'])
    
    response = llm.invoke([
        SystemMessage(content="You are a precise intent extraction system."),
        HumanMessage(content=prompt)
    ])
    
    # Parse JSON response
    try:
        intent = json.loads(response.content)
    except json.JSONDecodeError:
        # Fallback if GPT returns invalid JSON
        intent = {
            "product_type": None,
            "budget": None,
            "price_min": None,
            "price_max": None,
            "category": None,
            "eco_friendly": None
        }
    
    output_data = {"intent": intent}
    duration_ms = (time.time() - start_time) * 1000
    
    # Log step
    logger.log_step(
        node_name="router",
        input_data=input_data,
        output_data=output_data,
        duration_ms=duration_ms,
        metadata={
            "model": "gpt-4o",
            "prompt_length": len(prompt),
            "response_length": len(response.content)
        }
    )
    
    print(f"\n[ROUTER] Extracted intent: {intent}")
    
    return output_data