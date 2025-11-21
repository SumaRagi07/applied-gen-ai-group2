import json
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from ..prompts import PLANNER_PROMPT

load_dotenv()

def planner_node(state):
    """Decide which tools to call and with what parameters"""
    
    llm = ChatOpenAI(
        model="gpt-4o", 
        temperature=0,
        api_key=os.getenv("OPENAI_API_KEY")
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
    
    print(f"\n[PLANNER] Plan: {plan['plan']}")
    print(f"[PLANNER] Tools: {plan['tools_to_call']}")
    print(f"[PLANNER] RAG params: {plan.get('rag_params', {})}")
    
    return {
        "plan": plan['plan'],
        "tools_to_call": plan['tools_to_call'],
        "rag_params": plan.get('rag_params', {})
    }