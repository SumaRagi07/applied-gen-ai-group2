import json
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from ..prompts import SAFETY_PROMPT

load_dotenv()

def safety_node(state):
    """Check if query is safe and appropriate"""
    
    llm = ChatOpenAI(
        model="gpt-4o", 
        temperature=0,
        api_key=os.getenv("OPENAI_API_KEY")
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
    
    print(f"\n[SAFETY] Is safe: {is_safe}")
    if not is_safe:
        print(f"[SAFETY] Reason: {reason}")
    
    return {
        "is_safe": is_safe,
        "safety_reason": reason
    }