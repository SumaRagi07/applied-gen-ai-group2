from pydantic import BaseModel, Field
from typing import List, Optional

# RAG Search Schemas
class RagSearchRequest(BaseModel):
    query: str = Field(..., description="Search query")
    price_min: Optional[float] = Field(None, description="Minimum price filter")
    price_max: Optional[float] = Field(None, description="Maximum price filter")
    category: Optional[str] = Field(None, description="Category filter")
    eco_friendly: Optional[bool] = Field(None, description="Eco-friendly filter")
    top_k: int = Field(5, description="Number of results to return")

class Product(BaseModel):
    doc_id: str
    title: str
    price: float
    main_category: str
    eco_friendly: bool
    brand: str
    image_url: str
    product_url: str
    relevance_score: float

class RagSearchResponse(BaseModel):
    results: List[Product]
    total_found: int
    query_time_ms: float
    source: str = "private_catalog"

# Web Search Schemas
class WebSearchRequest(BaseModel):
    query: str = Field(..., description="Search query")
    max_results: int = Field(5, description="Maximum results to return")

class WebResult(BaseModel):
    title: str
    url: str
    snippet: str
    price: Optional[str] = None
    source: str

class WebSearchResponse(BaseModel):
    results: List[WebResult]
    total_found: int
    cached: bool
    query_time_ms: float
    source: str = "live_web"

# Tool Call Schemas
class ToolCallRequest(BaseModel):
    tool: str = Field(..., description="Tool name to execute")
    params: dict = Field(..., description="Tool parameters")

class ToolCallResponse(BaseModel):
    success: bool
    data: Optional[dict] = None
    error: Optional[str] = None
    execution_time_ms: float