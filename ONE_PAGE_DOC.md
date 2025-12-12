# Agentic Voice-to-Voice AI Assistant for Product Discovery (E-commerce)

## Project Overview
Voice-to-voice AI assistant for natural product queries. Processes spoken requests through a multi-agent LangGraph pipeline, retrieves from private Amazon Product Dataset 2020 catalog (8,661 products), compares with live web results via MCP tools, and responds via TTS with citations and safety checks.

## Architecture

**Multi-Agent LangGraph Pipeline** (Router → Safety → Planner → Executor → Reconciler → Synthesizer):
- **Router**: Extracts structured intent (product_type, budget, price_min/max, category, eco_friendly, materials, brand) from natural language
- **Safety**: Domain allowlist validation; blocks weapons, medical products, adult content; allows toy store queries
- **Planner**: Decides tool strategy (rag.search for facts, web.search for current prices/availability)
- **Executor**: Calls MCP tools via HTTP; handles caching, rate limiting
- **Reconciler**: Matches products by SKU/brand/title; flags price/availability conflicts; generates comparison table
- **Synthesizer**: Generates concise, cited recommendations (≤15s for TTS) with doc_ids and live URLs

**MCP Server** (FastAPI): Two-tool unified interface
- **rag.search**: Vector + metadata hybrid search over ChromaDB (8,661 products). Returns {sku, title, price, rating, brand, ingredients, doc_id}. Filters: price_min/max, category, eco_friendly, top_k. Uses OpenAI embeddings (text-embedding-3-small).
- **web.search**: Live web search via SerpAPI (Google Shopping). Returns {title, url, snippet, price, availability}. TTL caching (60-300s), rate limiting (100 req/min), logging.

**Agentic RAG**: Amazon Product Dataset 2020 (Household Cleaning) → 8,661 products indexed in ChromaDB. Embeddings: title + features + review snippets. Metadata: brand, price, category, rating, ingredients. Hybrid retrieval (vector similarity + metadata filters) with doc_id provenance.

**Speech Processing**: ASR via OpenAI Whisper (fragment-based, WAV/MP3). TTS via OpenAI TTS (fragment-based, ≤15s summaries). Multiple voices supported.

**UI** (Streamlit): Mic capture, live transcript, agent step log, comparison table, TTS playback, citation badges (private doc_ids + live URLs), eco-friendly theme.

## Technical Stack
LangGraph 1.0.3 | OpenAI GPT-4 (model-agnostic) | ChromaDB 1.3.4 | FastAPI 0.121.2 | SerpAPI | OpenAI Whisper/TTS | Streamlit 1.51.0 | In-memory caching (TTL-based) | Rate limiting (token bucket)

## Data Pipeline
EDA (`1_data_eda.ipynb`) → Cleaning (`2_data_cleaning.ipynb`) → Embedding Generation (`3_Embedding_VectorDatabase_generation.ipynb`) → ChromaDB (`vectordb/chroma/`)

## Key Features
Grounded responses (citations), conflict handling (price/availability reconciliation), safety (domain allowlist), caching (web: 60-300s TTL, rag: persistent), session logging (JSON in `logs/`), error handling (graceful degradation)

## Setup
**Prerequisites**: Python 3.9+, virtual environment, API keys (OpenAI, SerpAPI)  
**Environment**: `.env` with `OPENAI_API_KEY`, `SERPAPI_KEY`, `CHROMA_PATH`  
**Install**: `pip install -r requirements.txt`  
**Run MCP**: `python src/mcp_server/server.py` (port 8000)  
**Run UI**: `streamlit run ui_finalversion_1130.py`  
**Test**: `test_agents.py`, `test_mcp.py`, `test_voice.py`, `test_scenarios.py`

## Project Structure
```
src/agents/ (LangGraph nodes) | src/mcp_server/ (FastAPI + tools) | src/voice/ (ASR/TTS) | vectordb/chroma/ (8,661 products) | logs/ (session logs) | ui_finalversion_1130.py
```

## Example Interaction
**User (voice)**: "Recommend eco-friendly stainless-steel cleaner under $15"  
**Flow**: Router extracts {product_type: "cleaner", eco_friendly: true, price_max: 15.0} → Safety passes → Planner calls rag.search + web.search → Executor retrieves 5 catalog + 3 web → Reconciler matches 2, flags 1 price conflict → Synthesizer: "Top pick: Brand X Steel-Safe Eco Cleaner—plant-based, 4.6★, $12.49. Compared with 2 alternatives. Details on screen."  
**UI**: Comparison table, citations (doc_ids + URLs), TTS playback

## Prompt Disclosure
All prompts in `src/agents/prompts.py`: ROUTER_PROMPT (intent extraction), SAFETY_PROMPT (content safety rules), PLANNER_PROMPT (tool selection), RECONCILER_PROMPT (product matching, conflict detection), SYNTHESIZER_PROMPT (citation formatting, TTS summary ≤15s)

## Limitations & Future Work
Fragment-based ASR/TTS (non-streaming); single category (can expand); SerpAPI only (can add Brave/Bing); simple string matching (can improve with fuzzy/ML); rule-based safety (can add LLM classifier)

---
**Team**: Applied Gen AI Group 2 | **Framework**: LangGraph | **Dataset**: Amazon Product Dataset 2020 | **Status**: Production-Ready

