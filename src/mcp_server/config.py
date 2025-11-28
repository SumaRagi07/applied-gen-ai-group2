import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root (go up from src/mcp_server/ to project root)
project_root = Path(__file__).parent.parent.parent
env_path = project_root / ".env"
load_dotenv(dotenv_path=env_path, override=True)

class Config:
    # API Keys
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    BRAVE_API_KEY = os.getenv("BRAVE_API_KEY")
    
    # Paths
    # Default to relative path, or use absolute path from env
    default_chroma_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "vectordb", "chroma")
    CHROMA_PATH = os.getenv("CHROMA_PATH", default_chroma_path)
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