import requests
import time
import re
from typing import List
from urllib.parse import urlparse
import sys
sys.path.append('.')

from src.mcp_server.config import config
from src.mcp_server.schemas import WebSearchRequest, WebSearchResponse, WebResult
from src.mcp_server.utils.cache import web_cache
from src.mcp_server.utils.rate_limiter import web_rate_limiter

class WebSearchTool:
    def __init__(self):
        self.api_key = config.BRAVE_API_KEY
        self.base_url = "https://api.search.brave.com/res/v1/web/search"
    
    def execute(self, request: WebSearchRequest) -> WebSearchResponse:
        start_time = time.time()
        
        # Check cache first
        cache_key = f"web_search:{request.query}"
        cached_result = web_cache.get(cache_key)
        
        if cached_result:
            cached_result['cached'] = True
            cached_result['query_time_ms'] = round((time.time() - start_time) * 1000, 2)
            return WebSearchResponse(**cached_result)
        
        # Check rate limit
        if not web_rate_limiter.is_allowed():
            print("Rate limit exceeded for web search")
            return WebSearchResponse(
                results=[],
                total_found=0,
                cached=False,
                query_time_ms=0
            )
        
        try:
            # Make API call
            results = self._search_brave(request.query, request.max_results)
            web_rate_limiter.record_call()
            
            # Format results
            web_results = self._format_results(results)
            
            query_time = (time.time() - start_time) * 1000
            
            response_data = {
                'results': web_results,
                'total_found': len(web_results),
                'cached': False,
                'query_time_ms': round(query_time, 2)
            }
            
            # Cache the result
            web_cache.set(cache_key, response_data)
            
            return WebSearchResponse(**response_data)
        
        except Exception as e:
            print(f"Error in web search: {str(e)}")
            return WebSearchResponse(
                results=[],
                total_found=0,
                cached=False,
                query_time_ms=round((time.time() - start_time) * 1000, 2)
            )
    
    def _search_brave(self, query: str, max_results: int) -> dict:
        headers = {
            "Accept": "application/json",
            "X-Subscription-Token": self.api_key
        }
        
        params = {
            "q": query,
            "count": max_results
        }
        
        response = requests.get(
            self.base_url,
            headers=headers,
            params=params,
            timeout=10
        )
        
        response.raise_for_status()
        return response.json()
    
    def _format_results(self, api_response: dict) -> List[WebResult]:
        results = []
        
        web_results = api_response.get('web', {}).get('results', [])
        
        for item in web_results:
            title = item.get('title', '')
            url = item.get('url', '')
            description = item.get('description', '')
            
            # Extract price from description if present
            price = self._extract_price(description)
            
            # Extract domain as source
            source = urlparse(url).netloc.replace('www.', '')
            
            result = WebResult(
                title=title,
                url=url,
                snippet=description,
                price=price,
                source=source
            )
            results.append(result)
        
        return results
    
    def _extract_price(self, text: str) -> str:
        # Try to find price patterns like $19.99, $1,299.00
        price_pattern = r'\$\d{1,3}(?:,\d{3})*(?:\.\d{2})?'
        match = re.search(price_pattern, text)
        return match.group(0) if match else None

# Global instance
web_tool = None

def get_web_tool():
    global web_tool
    if web_tool is None:
        web_tool = WebSearchTool()
    return web_tool