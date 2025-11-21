import json
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from ..prompts import ROUTER_PROMPT

load_dotenv()

def router_node(state):
    """Extract structured intent from user query"""
    
    llm = ChatOpenAI(
        model="gpt-4o", 
        temperature=0,
        api_key=os.getenv("OPENAI_API_KEY")
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
    
    print(f"\n[ROUTER] Extracted intent: {intent}")
    
    return {"intent": intent}