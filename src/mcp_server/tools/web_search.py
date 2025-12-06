"""
Web search tool using Google Shopping API (via SerpAPI)
Replaces Brave Search for product price lookups
"""

import requests
import time
import os
from typing import List
from dotenv import load_dotenv
import sys
sys.path.append('.')

from src.mcp_server.config import config
from src.mcp_server.schemas import WebSearchRequest, WebSearchResponse, WebResult
from src.mcp_server.utils.cache import web_cache
from src.mcp_server.utils.rate_limiter import web_rate_limiter

load_dotenv()

class WebSearchTool:
    def __init__(self):
        self.api_key = os.getenv("SERPAPI_KEY")
        if not self.api_key:
            print("⚠️ Warning: SERPAPI_KEY not set. Web search will not work.")
        self.base_url = "https://serpapi.com/search"
    
    def execute(self, request: WebSearchRequest) -> WebSearchResponse:
        start_time = time.time()
        
        # Create CONSISTENT cache key (normalize query)
        cache_key = f"web_search:{request.query.lower().strip()}"
        cached_result = web_cache.get(cache_key)
        
        if cached_result:
            print(f"✅ [CACHE HIT] {request.query}")
            cached_result['cached'] = True
            cached_result['query_time_ms'] = round((time.time() - start_time) * 1000, 2)
            return WebSearchResponse(**cached_result)
        
        print(f"❌ [CACHE MISS] {request.query}")
        
        # Check rate limit
        if not web_rate_limiter.is_allowed():
            print("⚠️ Rate limit exceeded for web search")
            return WebSearchResponse(
                results=[],
                total_found=0,
                cached=False,
                query_time_ms=0
            )
        
        try:
            if not self.api_key:
                print("⚠️ Web search skipped: SERPAPI_KEY not set")
                return WebSearchResponse(
                    results=[],
                    total_found=0,
                    cached=False,
                    query_time_ms=round((time.time() - start_time) * 1000, 2)
                )
            
            # Make API call to Google Shopping
            results = self._search_google_shopping(request.query, request.max_results)
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
            print(f"💾 [CACHE SET] {request.query}")
            
            return WebSearchResponse(**response_data)
        
        except requests.exceptions.HTTPError as e:
            print(f"❌ HTTP Error in web search: {e.response.status_code}")
            return WebSearchResponse(
                results=[],
                total_found=0,
                cached=False,
                query_time_ms=round((time.time() - start_time) * 1000, 2)
            )
        except Exception as e:
            print(f"❌ Error in web search: {str(e)}")
            return WebSearchResponse(
                results=[],
                total_found=0,
                cached=False,
                query_time_ms=round((time.time() - start_time) * 1000, 2)
            )
    
    def _search_google_shopping(self, query: str, max_results: int) -> dict:
        """Search Google Shopping via SerpAPI"""
        params = {
            "engine": "google_shopping",
            "q": query,
            "api_key": self.api_key,
            "num": max_results,
            "hl": "en",
            "gl": "us"
        }
        
        response = requests.get(
            self.base_url,
            params=params,
            timeout=30
        )
        
        response.raise_for_status()
        return response.json()
    
    def _format_results(self, api_response: dict) -> List[WebResult]:
        """Format Google Shopping results"""
        results = []
        
        shopping_results = api_response.get('shopping_results', [])
        
        for item in shopping_results:
            title = item.get('title', '')
            url = item.get('product_link', '')
            
            # Build snippet from available info
            snippet_parts = []
            if item.get('source'):
                snippet_parts.append(f"Available from {item['source']}")
            if item.get('delivery'):
                snippet_parts.append(item['delivery'])
            if item.get('rating') and item.get('reviews'):
                snippet_parts.append(f"Rated {item['rating']}/5 ({item['reviews']} reviews)")
            
            snippet = ' · '.join(snippet_parts) if snippet_parts else ''
            
            # Get price (already formatted as "$19.99")
            price = item.get('price')
            
            # Get source/store name
            source = item.get('source', 'Unknown')
            
            # Get rating and reviews
            rating = item.get('rating')
            reviews = item.get('reviews')
            
            # ✅ GET THUMBNAIL IMAGE
            thumbnail = item.get('thumbnail')
            
            result = WebResult(
                title=title,
                url=url,
                snippet=snippet,
                price=price,
                source=source,
                rating=rating,
                reviews=reviews,
                thumbnail=thumbnail  # ✅ ADD THIS
            )
            results.append(result)
        
        return results


# Global instance
web_tool = None

def get_web_tool():
    global web_tool
    if web_tool is None:
        web_tool = WebSearchTool()
    return web_tool