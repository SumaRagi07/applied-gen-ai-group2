import requests
import time

MCP_BASE_URL = "http://localhost:8000"

def executor_node(state):
    """Execute the planned tool calls"""
    
    results = {}
    
    # Call rag.search if in plan
    if "rag.search" in state.get('tools_to_call', []):
        print(f"\n[EXECUTOR] Calling rag.search...")
        
        try:
            response = requests.post(
                f"{MCP_BASE_URL}/call",
                json={
                    "tool": "rag.search",
                    "params": state['rag_params']
                },
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data['success']:
                    results['rag_results'] = data['data']['results']
                    print(f"[EXECUTOR] RAG found: {len(results['rag_results'])} products")
                else:
                    results['rag_results'] = []
                    print(f"[EXECUTOR] RAG error: {data.get('error')}")
            else:
                results['rag_results'] = []
                print(f"[EXECUTOR] RAG HTTP error: {response.status_code}")
        
        except Exception as e:
            results['rag_results'] = []
            print(f"[EXECUTOR] RAG exception: {str(e)}")
    
    # Call web.search if in plan
    if "web.search" in state.get('tools_to_call', []):
        print(f"\n[EXECUTOR] Calling web.search...")
        
        # Add delay to respect rate limits
        time.sleep(2)
        
        try:
            response = requests.post(
                f"{MCP_BASE_URL}/call",
                json={
                    "tool": "web.search",
                    "params": {
                        "query": state['user_query'],
                        "max_results": 5
                    }
                },
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data['success']:
                    results['web_results'] = data['data']['results']
                    print(f"[EXECUTOR] Web found: {len(results['web_results'])} results")
                else:
                    results['web_results'] = []
                    print(f"[EXECUTOR] Web error: {data.get('error')}")
            else:
                results['web_results'] = []
                print(f"[EXECUTOR] Web HTTP error: {response.status_code}")
        
        except Exception as e:
            results['web_results'] = []
            print(f"[EXECUTOR] Web exception: {str(e)}")
    
    return results