import requests
import time
from ..utils.logger import get_logger

MCP_BASE_URL = "http://localhost:8000"

def executor_node(state):
    """Execute the planned tool calls"""
    start_time = time.time()
    logger = get_logger()
    
    input_data = {
        "tools_to_call": state.get('tools_to_call', []),
        "rag_params": state.get('rag_params', {}),
        "user_query": state.get('user_query', '')
    }
    
    results = {}
    
    # Call rag.search if in plan
    if "rag.search" in state.get('tools_to_call', []):
        print(f"\n[EXECUTOR] Calling rag.search...")
        tool_start = time.time()
        
        try:
            response = requests.post(
                f"{MCP_BASE_URL}/call",
                json={
                    "tool": "rag.search",
                    "params": state['rag_params']
                },
                timeout=10
            )
            
            tool_duration = (time.time() - tool_start) * 1000
            
            if response.status_code == 200:
                data = response.json()
                if data['success']:
                    results['rag_results'] = data['data']['results']
                    print(f"[EXECUTOR] RAG found: {len(results['rag_results'])} products")
                    
                    # Log tool call
                    logger.log_tool_call(
                        tool_name="rag.search",
                        params=state['rag_params'],
                        result={"count": len(results['rag_results']), "execution_time_ms": data.get('execution_time_ms', 0)},
                        duration_ms=tool_duration,
                        success=True
                    )
                else:
                    results['rag_results'] = []
                    print(f"[EXECUTOR] RAG error: {data.get('error')}")
                    logger.log_tool_call(
                        tool_name="rag.search",
                        params=state['rag_params'],
                        result={},
                        duration_ms=tool_duration,
                        success=False,
                        error=data.get('error')
                    )
            else:
                results['rag_results'] = []
                print(f"[EXECUTOR] RAG HTTP error: {response.status_code}")
                logger.log_tool_call(
                    tool_name="rag.search",
                    params=state['rag_params'],
                    result={},
                    duration_ms=tool_duration,
                    success=False,
                    error=f"HTTP {response.status_code}"
                )
        
        except Exception as e:
            results['rag_results'] = []
            print(f"[EXECUTOR] RAG exception: {str(e)}")
            logger.log_tool_call(
                tool_name="rag.search",
                params=state['rag_params'],
                result={},
                duration_ms=(time.time() - tool_start) * 1000,
                success=False,
                error=str(e)
            )
    
    # Call web.search if in plan
    if "web.search" in state.get('tools_to_call', []):
        print(f"\n[EXECUTOR] Calling web.search...")
        
        # Add delay to respect rate limits
        time.sleep(2)
        tool_start = time.time()
        
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
            
            tool_duration = (time.time() - tool_start) * 1000
            
            if response.status_code == 200:
                data = response.json()
                if data['success']:
                    results['web_results'] = data['data']['results']
                    print(f"[EXECUTOR] Web found: {len(results['web_results'])} results")
                    
                    # Log tool call
                    logger.log_tool_call(
                        tool_name="web.search",
                        params={"query": state['user_query'], "max_results": 5},
                        result={"count": len(results['web_results']), "cached": data['data'].get('cached', False), "execution_time_ms": data.get('execution_time_ms', 0)},
                        duration_ms=tool_duration,
                        success=True
                    )
                else:
                    results['web_results'] = []
                    print(f"[EXECUTOR] Web error: {data.get('error')}")
                    logger.log_tool_call(
                        tool_name="web.search",
                        params={"query": state['user_query']},
                        result={},
                        duration_ms=tool_duration,
                        success=False,
                        error=data.get('error')
                    )
            else:
                results['web_results'] = []
                print(f"[EXECUTOR] Web HTTP error: {response.status_code}")
                logger.log_tool_call(
                    tool_name="web.search",
                    params={"query": state['user_query']},
                    result={},
                    duration_ms=tool_duration,
                    success=False,
                    error=f"HTTP {response.status_code}"
                )
        
        except Exception as e:
            results['web_results'] = []
            print(f"[EXECUTOR] Web exception: {str(e)}")
            logger.log_tool_call(
                tool_name="web.search",
                params={"query": state['user_query']},
                result={},
                duration_ms=(time.time() - tool_start) * 1000,
                success=False,
                error=str(e)
            )
    
    output_data = results
    duration_ms = (time.time() - start_time) * 1000
    
    # Log step
    logger.log_step(
        node_name="executor",
        input_data=input_data,
        output_data=output_data,
        duration_ms=duration_ms,
        metadata={
            "rag_count": len(results.get('rag_results', [])),
            "web_count": len(results.get('web_results', []))
        }
    )
    
    return output_data