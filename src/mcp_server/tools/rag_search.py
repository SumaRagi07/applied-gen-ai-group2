import chromadb
from openai import OpenAI
import time
from typing import List, Dict, Any, Optional
import sys
sys.path.append('.')

from src.mcp_server.config import config
from src.mcp_server.schemas import RagSearchRequest, RagSearchResponse, Product
from src.mcp_server.utils.cache import rag_cache

class RagSearchTool:
    def __init__(self):
        print(f"Initializing RAG Search Tool...")
        print(f"ChromaDB path: {config.CHROMA_PATH}")
        
        # Validate API key
        if not config.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY not set in .env file")
        
        # Initialize OpenAI client (new API)
        self.openai_client = OpenAI(api_key=config.OPENAI_API_KEY)
        
        # Initialize ChromaDB
        self.client = chromadb.PersistentClient(path=config.CHROMA_PATH)
        self.collection = self.client.get_collection(name="products")
        
        print(f"Collection loaded: {self.collection.count()} products")
    
    def execute(self, request: RagSearchRequest) -> RagSearchResponse:
        start_time = time.time()
        
        # CHECK CACHE FIRST
        cache_key = self._create_cache_key(request)
        cached_result = rag_cache.get(cache_key)
        
        if cached_result:
            print(f"✅ [RAG CACHE HIT] {request.query}")
            cached_result['query_time_ms'] = round((time.time() - start_time) * 1000, 2)
            return RagSearchResponse(**cached_result)
        
        print(f"❌ [RAG CACHE MISS] {request.query}")
        
        try:
            # Generate query embedding
            query_embedding = self._generate_embedding(request.query)
            
            # Build metadata filters
            where_filter = self._build_filters(request)
            
            # Query ChromaDB (get more results to filter)
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=request.top_k * 2,  # Get 2x to filter for relevance
                where=where_filter if where_filter else None
            )
            
            # Format results WITH SMART TWO-TIER FILTERING
            products = self._format_results(results, request.top_k)
            
            query_time = (time.time() - start_time) * 1000
            
            # PREPARE RESPONSE DATA FOR CACHING
            response_data = {
                'results': [product.dict() for product in products],
                'total_found': len(products),
                'query_time_ms': round(query_time, 2),
                'source': 'private_catalog'
            }
            
            # CACHE THE RESULT
            rag_cache.set(cache_key, response_data)
            print(f"💾 [RAG CACHE SET] {request.query}")
            
            return RagSearchResponse(
                results=products,
                total_found=len(products),
                query_time_ms=round(query_time, 2)
            )
        
        except Exception as e:
            print(f"❌ Error in RAG search: {str(e)}")
            return RagSearchResponse(
                results=[],
                total_found=0,
                query_time_ms=round((time.time() - start_time) * 1000, 2)
            )
    
    def _create_cache_key(self, request: RagSearchRequest) -> str:
        """Create consistent cache key from request parameters"""
        # Normalize query
        query = request.query.lower().strip()
        
        # Include all filter parameters in cache key
        key_parts = [
            f"query:{query}",
            f"price_min:{request.price_min}",
            f"price_max:{request.price_max}",
            f"category:{request.category}",
            f"eco:{request.eco_friendly}",
            f"top_k:{request.top_k}"
        ]
        
        cache_key = "rag_search:" + "|".join(key_parts)
        return cache_key
    
    def _generate_embedding(self, text: str) -> List[float]:
        # Use new OpenAI client API
        response = self.openai_client.embeddings.create(
            model=config.EMBEDDING_MODEL,
            input=text
        )
        return response.data[0].embedding
    
    def _build_filters(self, request: RagSearchRequest) -> Optional[Dict[str, Any]]:
        filters = []
        
        if request.price_min is not None:
            filters.append({"price": {"$gte": request.price_min}})
        
        if request.price_max is not None:
            filters.append({"price": {"$lte": request.price_max}})
        
        if request.category is not None:
            filters.append({"main_category": {"$eq": request.category}})
        
        if request.eco_friendly is not None:
            filters.append({"eco_friendly": {"$eq": request.eco_friendly}})
        
        if len(filters) == 0:
            return None
        elif len(filters) == 1:
            return filters[0]
        else:
            return {"$and": filters}
    
    def _format_results(self, results: Dict, top_k: int) -> List[Product]:
        """Format results with smart two-tier filtering"""
        products = []
        
        if not results['ids'] or len(results['ids'][0]) == 0:
            return products
        
        # ✅ TWO-TIER THRESHOLD SYSTEM
        HARD_THRESHOLD = 1.3  # Absolute cutoff - filter complete nonsense
        SOFT_THRESHOLD = 1.1  # Warning threshold - flag low confidence
        
        low_confidence_count = 0
        filtered_count = 0
        
        for i in range(len(results['ids'][0])):
            metadata = results['metadatas'][0][i]
            distance = results['distances'][0][i]
            
            # ✅ HARD FILTER: Remove complete nonsense (distance > 1.2)
            if distance > HARD_THRESHOLD:
                filtered_count += 1
                print(f"[RAG] ✗ Filtered: '{metadata['title'][:40]}...' (distance: {distance:.3f}, too irrelevant)")
                continue
            
            # ✅ SOFT WARNING: Flag low confidence but include (0.85 < distance < 1.2)
            if distance > SOFT_THRESHOLD:
                low_confidence_count += 1
                print(f"[RAG] ⚠ Low confidence: '{metadata['title'][:40]}...' (distance: {distance:.3f})")
            else:
                print(f"[RAG] ✓ Good match: '{metadata['title'][:40]}...' (distance: {distance:.3f})")
            
            # Convert distance to similarity score
            relevance_score = 1 - distance
            
            product = Product(
                doc_id=results['ids'][0][i],
                title=metadata['title'],
                price=metadata['price'],
                main_category=metadata['main_category'],
                eco_friendly=metadata['eco_friendly'],
                brand=metadata['brand'],
                image_url=metadata['image_url'],
                product_url=metadata['product_url'],
                relevance_score=round(relevance_score, 4)
            )
            products.append(product)
            
            # ✅ STOP WHEN WE HAVE ENOUGH RELEVANT RESULTS
            if len(products) >= top_k:
                break
        
        # ✅ SMART DECISION: If ALL results are low confidence, return EMPTY
        if products and low_confidence_count == len(products):
            print(f"[RAG] ⚠️ All {len(products)} results have low confidence (distance > {SOFT_THRESHOLD})")
            print(f"[RAG] → Likely irrelevant query, returning EMPTY to trigger web-only response")
            return []
        
        # Log summary
        if filtered_count > 0:
            print(f"[RAG] Filtered {filtered_count} irrelevant results")
        if len(products) == 0:
            print(f"[RAG] No relevant products found")
        else:
            print(f"[RAG] Returning {len(products)} products ({low_confidence_count} low confidence)")
        
        return products


# Global instance
rag_tool = None

def get_rag_tool():
    global rag_tool
    if rag_tool is None:
        rag_tool = RagSearchTool()
    return rag_tool
