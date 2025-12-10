# Agentic Voice-to-Voice AI Assistant for Product Discovery

An Agentic AI system that enables voice-to-voice product discovery with real-time price comparison, powered by LangGraph, OpenAI, and ChromaDB.

## Overview

This project implements an intelligent product search assistant that:
- **Accepts voice or text queries** for product searches
- **Searches a product catalog** (Amazon Product Dataset 2020) using RAG
- **Fetches current prices** from the web using SerpAPI
- **Reconciles and compares** historical v.s. current prices
- **Generates voice responses** with product recommendations
- **Provides a Streamlit UI** with real-time progress tracking

## Key Features

### Voice Interface
- **Speech-to-Text (ASR)**: Record audio or upload files for transcription
- **Text-to-Speech (TTS)**: Natural voice responses with multiple voice options
- **Background Recording**: Continuous audio recording with live timer

### Multi-Agent Architecture
- **Router**: Extracts intent and query type from user input
- **Safety**: Content moderation to filter inappropriate queries
- **Planner**: Strategically plans search operations
- **Executor**: Executes RAG and web searches
- **Reconciler**: Matches products and detects price conflicts
- **Synthesizer**: Generates comprehensive answers with citations

### Product Intelligence
- **Price Comparison**: Historical (2020) vs. current prices
- **Conflict Detection**: Flags significant price discrepancies
- **Product Matching**: Fuzzy matching between catalog and web results
- **Rich Product Cards**: Images, ratings, reviews, and direct purchase links

### Search Capabilities
- **RAG Search**: Semantic search over products with filters
- **Web Search**: Real-time product information via SerpAPI (Google Shopping)
- **Caching**: Intelligent caching for faster repeated queries

### Monitoring & Logging
- **Comprehensive Logging**: JSON logs for all agent steps
- **Execution Statistics**: Duration tracking, tool call metrics
- **Real-time Progress**: Live UI updates during processing
- **Agent Execution Logs**: Detailed step-by-step breakdown

## Architecture

### System Components

```
┌─────────────────┐
│  Streamlit UI   │
│   (app.py)      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  LangGraph      │
│  Multi-Agent    │
│  Workflow       │
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
    ▼         ▼
┌────────┐ ┌──────────┐
│  MCP   │ │  Voice   │
│ Server │ │  Module  │
└───┬────┘ └──────────┘
    │
    ├──► RAG Search (ChromaDB)
    └──► Web Search (SerpAPI)
```

### Agent Workflow

```
User Query
    │
    ▼
┌─────────┐
│ Router  │ ──► Extract intent & query type
└────┬────┘
     │
     ▼
┌─────────┐
│ Safety  │ ──► Content moderation
└────┬────┘
     │
     ▼
┌─────────┐
│ Planner │ ──► Plan search strategy
└────┬────┘
     │
     ▼
┌─────────┐
│Executor │ ──► Execute RAG + Web searches
└────┬────┘
     │
     ▼
┌────────────┐
│ Reconciler │ ──► Match products & detect conflicts
└────┬───────┘
     │
     ▼
┌────────────┐
│Synthesizer │ ──► Generate answer + TTS summary
└────┬───────┘
     │
     ▼
  Results
```

## Quick Start

### Prerequisites

- Python 3.9+ (3.10+ recommended)
- Git
- OpenAI API key
- SerpAPI key (for Google Shopping search)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/SumaRagi07/applied-gen-ai-group2
   cd applied-gen-ai-group2
   ```

2. **Set up environment variables**
   
   Create a `.env` file in the project root:
   ```bash
   OPENAI_API_KEY=sk-proj-your-actual-key-here
   SERPAPI_KEY=your-serpapi-key-here
   CHROMA_PATH=./vectordb/chroma
   ```

3. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

4. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

5. **Test the setup**
   
   **Terminal 1** - Start MCP Server:
   ```bash
   python src/mcp_server/server.py
   ```
   
   You should see:
   ```
   Starting MCP Server...
   ✓ RAG Search tool initialized
   ✓ Web Search tool initialized
   Server ready on http://0.0.0.0:8000
   ```

6. **Run the Streamlit app**
   ```bash
   streamlit run app.py
   ```

## Usage

### Web Interface

1. **Start the MCP server** (Terminal 1):
   ```bash
   python src/mcp_server/server.py
   ```

2. **Launch Streamlit UI** (Terminal 2):
   ```bash
   streamlit run app.py
   ```

3. **Use the interface**:
   - **Record**: Click "Start Recording" and speak your query
   - **Upload**: Upload an audio file (WAV, MP3, M4A)
   - **Type**: Enter your query directly in the text field

4. **View results**:
   - Audio summary (15-second voice response)
   - Product cards with images and prices
   - Price comparison tables
   - Full detailed answer
   - Agent execution logs
   - Citations and sources

## Project Structure

```
applied-gen-ai-group2/
├── app.py                          # Streamlit UI application
├── requirements.txt                # Python dependencies
├── .env.example                    # Environment variables (change to .env after putting the key and path)
│
├── src/
│   ├── agents/                     # Multi-agent system
│   │   ├── graph.py                # LangGraph workflow definition
│   │   ├── state.py                # State schema
│   │   ├── prompts.py               # LLM prompts for each node
│   │   ├── nodes/                   # Agent nodes
│   │   │   ├── router.py            # Intent extraction
│   │   │   ├── safety.py            # Content moderation
│   │   │   ├── planner.py           # Search planning
│   │   │   ├── executor.py          # Tool execution
│   │   │   ├── reconciler.py        # Product reconciliation
│   │   │   └── synthesizer.py       # Answer generation
│   │   └── utils/
│   │       └── logger.py            # Logging system
│   │
│   ├── mcp_server/                 # Model Context Protocol server
│   │   ├── server.py                # FastAPI server
│   │   ├── config.py                # Configuration
│   │   ├── schemas.py               # Request/response schemas
│   │   ├── tools/
│   │   │   ├── rag_search.py        # RAG search tool
│   │   │   └── web_search.py        # Web search tool
│   │   └── utils/
│   │       ├── cache.py             # Caching utilities
│   │       └── rate_limiter.py      # Rate limiting
│   │
│   └── voice/                       # Voice processing
│       ├── asr.py                   # Speech-to-text
│       └── tts.py                   # Text-to-speech
│
├── vectordb/                        # Vector database
│   └── chroma/                      # ChromaDB instance
│
├── logs/                            # Agent execution logs
│
├── *.ipynb                          # Data processing notebooks
│
└── test_*.py                        # Test scripts
```

## API Keys

### OpenAI API Key
1. Visit https://platform.openai.com/api-keys
2. Sign in or create an account
3. Click "Create new secret key"
4. Copy the key (starts with `sk-`)

### SerpAPI Key
1. Visit https://serpapi.com/
2. Sign up for free account (100 searches/month)
3. Get your API key from dashboard
4. Copy the key

## Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `OPENAI_API_KEY` | OpenAI API key for LLM and embeddings | Yes |
| `SERPAPI_KEY` | SerpAPI key for Google Shopping search | Yes |
| `CHROMA_PATH` | Path to ChromaDB directory | Yes |

### MCP Server Configuration

Edit `src/mcp_server/config.py` to change:
- Server host (default: `0.0.0.0`)
- Server port (default: `8000`)
- Cache settings
- Rate limiting

## Key Features Explained

### Product Reconciliation

The reconciler node matches products between the catalog (2020) and current web results:
- **Fuzzy Matching**: Uses brand names (40%) and titles (60%) with similarity scoring
- **Conflict Detection**: Flags price discrepancies >20% or >$5
- **Unified Table**: Creates comparison table with matched, catalog-only, and web-only products

### Logging System

Comprehensive logging tracks:
- **Step Execution**: Each agent node with timestamps
- **Tool Calls**: RAG and web search requests/responses
- **Execution Statistics**: Total duration, average time per step
- **JSON Logs**: Saved to `logs/` directory for analysis

### TTS Summary Generation

The synthesizer creates concise 15-second voice summaries:
- Uses actual product prices
- Natural citation formatting for speech
- Conversational format

## Troubleshooting

### Common Issues

**"OPENAI_API_KEY environment variable not set"**
- Ensure `.env` file exists (not `.env.example`)
- Check that `OPENAI_API_KEY=sk-...` is set
- Restart terminal/IDE after creating `.env`

**"404 Not Found" when testing MCP server**
- Start MCP server: `python src/mcp_server/server.py`
- Verify it's running on `http://localhost:8000`
- Wait a few seconds after starting before testing

**"Connection refused" or "Connection error"**
- Start MCP server first in Terminal 1
- Check if port 8000 is in use: `lsof -i :8000` (macOS/Linux)
- Verify `CHROMA_PATH` points to correct directory (relative or absolute path both work)

**Module not found errors**
- Activate virtual environment: `source venv/bin/activate`
- Reinstall dependencies: `pip install -r requirements.txt`

**ChromaDB errors**
- Verify `CHROMA_PATH` points to correct directory
- Ensure `vectordb/chroma/` directory exists
- Check file permissions

## License

This project is part of the Applied Generative AI course at the University of Chicago.

