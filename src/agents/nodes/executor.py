import requests
import time
import re
import concurrent.futures
from ..utils.logger import get_logger

MCP_BASE_URL = "http://localhost:8000"

def _extract_price(price_str):
    """Extract numeric price from string like '$12.99'"""
    if not price_str:
        return None
    price_clean = re.sub(r'[^\d.]', '', str(price_str))
    try:
        return float(price_clean)
    except (ValueError, TypeError):
        return None

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
                timeout=35
            )
            
            tool_duration = (time.time() - tool_start) * 1000
            
            if response.status_code == 200:
                data = response.json()
                if data['success']:
                    results['rag_results'] = data['data']['results']
                    print(f"[EXECUTOR] RAG found: {len(results['rag_results'])} products")
                    
                    logger.log_tool_call(
                        tool_name="rag.search",
                        params=state['rag_params'],
                        result={"count": len(results['rag_results'])},
                        duration_ms=tool_duration,
                        success=True
                    )
                else:
                    results['rag_results'] = []
                    print(f"[EXECUTOR] RAG error: {data.get('error')}")
            else:
                results['rag_results'] = []
                print(f"[EXECUTOR] RAG HTTP error: {response.status_code}")
        
        except Exception as e:
            results['rag_results'] = []
            print(f"[EXECUTOR] RAG exception: {str(e)}")
    
    # Call web.search if in plan - WITH PARALLELIZATION AND PRICE FILTERING
    if "web.search" in state.get('tools_to_call', []):
        print(f"\n[EXECUTOR] Calling web.search (Google Shopping via MCP)...")
        
        web_results = []
        rag_results_list = results.get('rag_results', [])
        
        # Get price constraints from intent
        intent = state.get('intent', {})
        price_max = intent.get('price_max')
        price_min = intent.get('price_min')
        
        if price_max:
            print(f"[EXECUTOR] Price filter: under ${price_max}")
        
        if rag_results_list:
            # ✅ Prepare queries for top 5 products (TRUNCATE LONG TITLES)
            queries = [
                product.get('title', '')[:60]  # Truncate to 60 chars to prevent complex searches
                for product in rag_results_list[:5]
            ]
            
            print(f"[EXECUTOR] Running {len(queries)} price checks in PARALLEL...")
            parallel_start = time.time()
            
            # ✅ Define function with better error handling
            def call_web_search(query):
                try:
                    time.sleep(1)  # Rate limit delay
                    response = requests.post(
                        f"{MCP_BASE_URL}/call",
                        json={
                            "tool": "web.search",
                            "params": {
                                "query": query,
                                "max_results": 30
                            }
                        },
                        timeout=35  # ✅ 35 seconds timeout
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        if data['success']:
                            return data['data']['results']
                    return []
                except requests.exceptions.Timeout:
                    print(f"[EXECUTOR] ⏱️ Timeout for {query[:30]}... (skipped)")
                    return []
                except requests.exceptions.ConnectionError:
                    print(f"[EXECUTOR] 🔌 Connection error for {query[:30]}... (skipped)")
                    return []
                except Exception as e:
                    print(f"[EXECUTOR] ❌ Error for {query[:40]}: {e}")
                    return []
            
            # Execute in parallel
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                future_to_query = {
                    executor.submit(call_web_search, query): query
                    for query in queries
                }
                
                for future in concurrent.futures.as_completed(future_to_query):
                    query = future_to_query[future]
                    try:
                        price_results = future.result()
                        if price_results:  # ✅ Only log if we got results
                            web_results.extend(price_results)
                            print(f"[EXECUTOR] ✓ {query[:40]}... → {len(price_results)} results")
                        else:
                            print(f"[EXECUTOR] ⊘ {query[:40]}... → 0 results (timeout or error)")
                    except Exception as e:
                        print(f"[EXECUTOR] ✗ {query[:40]}... → Error: {e}")
            
            parallel_duration = (time.time() - parallel_start) * 1000
            print(f"[EXECUTOR] Parallel checks done in {parallel_duration:.0f}ms")
        
        # ✅ USE FULL USER QUERY for alternatives (more specific than product_type)
        user_query = state.get('user_query', '')
        
        # Use user's actual query words
        general_query = user_query.lower()
        
        # Add eco-friendly if specified in intent
        if intent.get('eco_friendly') and 'eco' not in general_query:
            general_query = f"eco-friendly {general_query}"
        
        print(f"[EXECUTOR] Searching alternatives: '{general_query}'...")
        time.sleep(0.5)
        
        try:
            tool_start = time.time()
            response = requests.post(
                f"{MCP_BASE_URL}/call",
                json={
                    "tool": "web.search",
                    "params": {
                        "query": general_query,
                        "max_results": 30
                    }
                },
                timeout=35  # ✅ 35 seconds timeout
            )
            
            tool_duration = (time.time() - tool_start) * 1000
            
            if response.status_code == 200:
                data = response.json()
                if data['success']:
                    alt_results = data['data']['results']
                    web_results.extend(alt_results)
                    print(f"[EXECUTOR] Found {len(alt_results)} alternatives")
                    
                    logger.log_tool_call(
                        tool_name="web.search",
                        params={"query": general_query, "max_results": 30},
                        result={"count": len(alt_results), "cached": data['data'].get('cached', False)},
                        duration_ms=tool_duration,
                        success=True
                    )
        except requests.exceptions.Timeout:
            print(f"[EXECUTOR] ⏱️ Timeout for alternatives search (skipped)")
        except Exception as e:
            print(f"[EXECUTOR] Error in alternatives search: {e}")
        
        # ✅ FILTER BY PRICE
        if price_max or price_min:
            original_count = len(web_results)
            filtered_results = []
            
            for result in web_results:
                price = _extract_price(result.get('price'))
                if price:
                    passes_filter = True
                    if price_max and price > price_max:
                        passes_filter = False
                    if price_min and price < price_min:
                        passes_filter = False
                    
                    if passes_filter:
                        filtered_results.append(result)
            
            web_results = filtered_results
            print(f"[EXECUTOR] Price filter: {original_count} → {len(web_results)} results (${price_min or 0}-${price_max or '∞'})")
        
        results['web_results'] = web_results
        print(f"[EXECUTOR] Total: {len(web_results)} web results")
    
    output_data = results
    duration_ms = (time.time() - start_time) * 1000
    
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