import chromadb
import openai
import time
from typing import List, Dict, Any, Optional
import sys
sys.path.append('.')

from src.mcp_server.config import config
from src.mcp_server.schemas import RagSearchRequest, RagSearchResponse, Product

class RagSearchTool:
    def __init__(self):
        print(f"Initializing RAG Search Tool...")
        print(f"ChromaDB path: {config.CHROMA_PATH}")
        
        self.client = chromadb.PersistentClient(path=config.CHROMA_PATH)
        self.collection = self.client.get_collection(name="products")
        openai.api_key = config.OPENAI_API_KEY
        
        print(f"Collection loaded: {self.collection.count()} products")
    
    def execute(self, request: RagSearchRequest) -> RagSearchResponse:
        start_time = time.time()
        
        try:
            # Generate query embedding
            query_embedding = self._generate_embedding(request.query)
            
            # Build metadata filters
            where_filter = self._build_filters(request)
            
            # Query ChromaDB
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=request.top_k,
                where=where_filter if where_filter else None
            )
            
            # Format results
            products = self._format_results(results)
            
            query_time = (time.time() - start_time) * 1000
            
            return RagSearchResponse(
                results=products,
                total_found=len(products),
                query_time_ms=round(query_time, 2)
            )
        
        except Exception as e:
            print(f"Error in RAG search: {str(e)}")
            raise
    
    def _generate_embedding(self, text: str) -> List[float]:
        response = openai.embeddings.create(
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
    
    def _format_results(self, results: Dict) -> List[Product]:
        products = []
        
        if not results['ids'] or len(results['ids'][0]) == 0:
            return products
        
        for i in range(len(results['ids'][0])):
            metadata = results['metadatas'][0][i]
            distance = results['distances'][0][i]
            
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
        
        return products

# Global instance (will be initialized when imported)
rag_tool = None

def get_rag_tool():
    global rag_tool
    if rag_tool is None:
        rag_tool = RagSearchTool()
    return rag_tool