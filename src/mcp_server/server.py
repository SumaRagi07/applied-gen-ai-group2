from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import time
import sys
sys.path.append('.')

from src.mcp_server.schemas import (
    ToolCallRequest, 
    ToolCallResponse,
    RagSearchRequest,
    WebSearchRequest
)
from src.mcp_server.tools.rag_search import get_rag_tool
from src.mcp_server.tools.web_search import get_web_tool
from src.mcp_server.config import config

# Initialize FastAPI app
app = FastAPI(
    title="MCP Server",
    description="Model Context Protocol Server with RAG and Web Search tools",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize tools on startup
@app.on_event("startup")
async def startup_event():
    print("Starting MCP Server...")
    print(f"Initializing tools...")
    
    # Initialize RAG tool
    try:
        get_rag_tool()
        print("✓ RAG Search tool initialized")
    except Exception as e:
        print(f"✗ Failed to initialize RAG tool: {e}")
    
    # Initialize Web tool
    try:
        get_web_tool()
        print("✓ Web Search tool initialized")
    except Exception as e:
        print(f"✗ Failed to initialize Web tool: {e}")
    
    print(f"Server ready on http://{config.MCP_HOST}:{config.MCP_PORT}")

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "ok", "message": "MCP Server is running"}

# Tool discovery endpoint
@app.get("/tools")
async def list_tools():
    return {
        "tools": [
            {
                "name": "rag.search",
                "description": "Search private product catalog (8,661 products from 2020)",
                "parameters": {
                    "query": {"type": "string", "required": True, "description": "Search query"},
                    "price_min": {"type": "float", "required": False, "description": "Minimum price filter"},
                    "price_max": {"type": "float", "required": False, "description": "Maximum price filter"},
                    "category": {"type": "string", "required": False, "description": "Category filter"},
                    "eco_friendly": {"type": "boolean", "required": False, "description": "Eco-friendly filter"},
                    "top_k": {"type": "integer", "required": False, "default": 5, "description": "Number of results"}
                }
            },
            {
                "name": "web.search",
                "description": "Search live web for current product information",
                "parameters": {
                    "query": {"type": "string", "required": True, "description": "Search query"},
                    "max_results": {"type": "integer", "required": False, "default": 5, "description": "Max results"}
                }
            }
        ]
    }

# Tool execution endpoint
@app.post("/call")
async def call_tool(request: ToolCallRequest):
    start_time = time.time()
    
    try:
        if request.tool == "rag.search":
            # Parse and validate params
            rag_request = RagSearchRequest(**request.params)
            
            # Execute tool
            rag_tool = get_rag_tool()
            result = rag_tool.execute(rag_request)
            
            execution_time = (time.time() - start_time) * 1000
            
            return ToolCallResponse(
                success=True,
                data=result.model_dump(),
                error=None,
                execution_time_ms=round(execution_time, 2)
            )
        
        elif request.tool == "web.search":
            # Parse and validate params
            web_request = WebSearchRequest(**request.params)
            
            # Execute tool
            web_tool = get_web_tool()
            result = web_tool.execute(web_request)
            
            execution_time = (time.time() - start_time) * 1000
            
            return ToolCallResponse(
                success=True,
                data=result.model_dump(),
                error=None,
                execution_time_ms=round(execution_time, 2)
            )
        
        else:
            raise HTTPException(
                status_code=404,
                detail=f"Tool '{request.tool}' not found"
            )
    
    except Exception as e:
        execution_time = (time.time() - start_time) * 1000
        
        return ToolCallResponse(
            success=False,
            data=None,
            error=str(e),
            execution_time_ms=round(execution_time, 2)
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=config.MCP_HOST,
        port=config.MCP_PORT,
        log_level="info"
    )