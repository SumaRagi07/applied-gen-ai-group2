import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

class Config:
    # API Keys
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    BRAVE_API_KEY = os.getenv("BRAVE_API_KEY")
    
    # Paths
    CHROMA_PATH = os.getenv("CHROMA_PATH", "/Users/sumasreeragi/Desktop/UChicago/Quarter 4/Gen AI/Final Project/vectordb/chroma")
    LOG_DIR = Path("logs")
    
    # Server settings
    MCP_HOST = "0.0.0.0"
    MCP_PORT = 8000
    
    # Cache settings
    CACHE_TTL_SECONDS = 300
    
    # Rate limiting
    RATE_LIMIT_PER_MINUTE = 10
    
    # Search settings
    DEFAULT_TOP_K = 5
    EMBEDDING_MODEL = "text-embedding-3-small"
    EMBEDDING_DIMENSION = 1536

config = Config()