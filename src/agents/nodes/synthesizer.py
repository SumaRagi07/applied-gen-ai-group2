#synthesizer.py
import json
import os
import re
import time
from pathlib import Path
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from ..prompts import SYNTHESIZER_PROMPT
from ..utils.logger import get_logger

# Load .env from project root
project_root = Path(__file__).parent.parent.parent.parent
env_path = project_root / ".env"
load_dotenv(dotenv_path=env_path, override=True)

def synthesizer_node(state):
    """Generate final answer with citations"""
    start_time = time.time()
    logger = get_logger()
    
    input_data = {
        "user_query": state.get('user_query', ''),
        "rag_count": len(state.get('rag_results', [])),
        "web_count": len(state.get('web_results', [])),
        "comparison_table_count": len(state.get('comparison_table', []))
    }
    
    # ✅ UPDATED: If query was unsafe, return error message WITH TTS
    if not state.get('is_safe', True):
        safety_reason = state.get('safety_reason', 'Content policy violation.')
        
        # Create user-friendly message
        error_message = (
            f"I'm sorry, but I can't help with that request. {safety_reason}"
        )
        
        # ✅ CREATE TTS SUMMARY for unsafe query
        tts_message = (
            "I'm sorry, I can't help with that request. "
            "This query violates our content safety policies."
        )
        
        output_data = {
            "final_answer": error_message,
            "citations": [],
            "tts_summary": tts_message  # ✅ Changed from None
        }
        duration_ms = (time.time() - start_time) * 1000
        logger.log_step(
            node_name="synthesizer",
            input_data=input_data,
            output_data=output_data,
            duration_ms=duration_ms,
            metadata={"reason": "Unsafe query blocked"}
        )
        return output_data
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or api_key.startswith("your_") or "placeholder" in api_key.lower():
        raise ValueError(f"Invalid OPENAI_API_KEY in .env file")
    
    llm = ChatOpenAI(
        model="gpt-4o", 
        temperature=0.3,
        api_key=api_key
    )
    
    # Format results for prompt
    rag_results = state.get('rag_results', [])
    web_results = state.get('web_results', [])
    comparison_table = state.get('comparison_table', [])
    conflicts = state.get('conflicts', [])
    
    # Store for TTS summary generation
    tts_rag_results = rag_results
    tts_web_results = web_results
    tts_comparison_table = comparison_table
    
    # ✅ Helper function to format comparison table cleanly
    def format_comparison_table(table):
        """Format comparison table as clean readable text to prevent formatting issues"""
        if not table:
            return "No matches"
        
        formatted = []
        for i, item in enumerate(table[:20], 1):
            lines = [f"\n=== Product {i} ==="]
            lines.append(f"Title: {item.get('title', 'Unknown')}")
            
            doc_id = item.get('catalog_id')
            if doc_id:
                lines.append(f"Citation: [doc_{doc_id}]")
            
            catalog_price = item.get('catalog_price')
            web_price = item.get('web_price')
            
            if catalog_price:
                lines.append(f"2020 Catalog Price: ${catalog_price:.2f}")
            
            if web_price:
                source = item.get('web_source', 'Unknown')
                lines.append(f"Current Web Price: ${web_price:.2f}")
                lines.append(f"Source: {source}")
            
            if catalog_price and web_price:
                diff_pct = ((web_price - catalog_price) / catalog_price) * 100
                direction = "increased" if diff_pct > 0 else "decreased"
                lines.append(f"Price Change: {direction} {abs(diff_pct):.0f}% since 2020")
            
            # Add type info
            item_type = item.get('type', 'matched')
            if item_type == 'catalog_only':
                lines.append("Status: Catalog only (not found online)")
            elif item_type == 'web_only':
                lines.append("Status: Web alternative (not in catalog)")
            
            formatted.append("\n".join(lines))
        
        return "\n".join(formatted)
    
    # ✅ SEND PRE-FORMATTED DATA (prevents LLM from mangling the format)
    rag_summary = json.dumps(rag_results, indent=2) if rag_results else "No results"
    web_summary = json.dumps(web_results[:10], indent=2) if web_results else "No results"
    comparison_summary = format_comparison_table(comparison_table)
    conflicts_summary = json.dumps(conflicts, indent=2) if conflicts else "No conflicts detected"
    
    prompt = SYNTHESIZER_PROMPT.format(
        query=state['user_query'],
        rag_results=rag_summary,
        web_results=web_summary,
        comparison_table=comparison_summary,
        conflicts=conflicts_summary
    )
    
    response = llm.invoke([
        SystemMessage(content="You are a helpful product recommendation assistant. Follow the formatting instructions in the prompt exactly as specified."),
        HumanMessage(content=prompt)
    ])
   
    answer = response.content
    
    # ✅ EXTRACT ALL CITATIONS - including store names without dots
    citations = []
    seen_citations = set()

    # 1. Extract doc_ids (format: [doc_00123])
    doc_ids = re.findall(r'\[doc_\d+\]', answer)
    for doc_id in doc_ids:
        if doc_id not in seen_citations:
            citations.append(doc_id)
            seen_citations.add(doc_id)

    # 2. Extract full URLs in markdown format
    urls_markdown = re.findall(r'\]\((https?://[^\)]+)\)', answer)
    for url in urls_markdown:
        if url not in seen_citations:
            citations.append(url)
            seen_citations.add(url)

    # 3. Extract URLs in square brackets
    urls_brackets = re.findall(r'\[(https?://[^\]]+)\]', answer)
    for url in urls_brackets:
        if url not in seen_citations:
            citations.append(url)
            seen_citations.add(url)

    # 4. Extract ANY text in brackets (store names, domains, etc.)
    all_brackets = re.findall(r'\[([^\]]+)\]', answer)
    for item in all_brackets:
        # Skip doc_ids and URLs (already captured)
        if not item.startswith('doc_') and not item.startswith('http'):
            if item not in seen_citations:
                citations.append(f"[{item}]")
                seen_citations.add(item)

    print(f"\n[SYNTHESIZER] Generated answer with {len(citations)} unique citations")
    
    # ✅ ADD: Extract web sources from comparison table (DEDUPLICATED)
    web_sources_set = set()
    for item in comparison_table[:20]:
        web_source = item.get('web_source')
        if web_source:
            # Clean up source (remove extra info after dash)
            clean_source = web_source.split(' -')[0].strip()
            web_sources_set.add(clean_source)

    # Add unique web sources to citations
    for source in sorted(web_sources_set):
        if source not in seen_citations:
            citations.append(source)
            seen_citations.add(source)

    print(f"[SYNTHESIZER] Total citations (with {len(web_sources_set)} unique web sources): {len(citations)}")
    
    # Generate TTS summary (≤15 seconds) with structured product data
    tts_summary = _create_tts_summary_with_data(
        answer, 
        citations, 
        tts_rag_results[:3] if tts_rag_results else [],
        tts_web_results[:3] if tts_web_results else [],
        tts_comparison_table[:3] if tts_comparison_table else [],
        max_words=40
    )
    
    output_data = {
        "final_answer": answer,
        "citations": citations,
        "tts_summary": tts_summary
    }
    duration_ms = (time.time() - start_time) * 1000
    
    # Log step
    logger.log_step(
        node_name="synthesizer",
        input_data=input_data,
        output_data={
            "answer_length": len(answer),
            "citations_count": len(citations),
            "tts_summary_length": len(tts_summary) if tts_summary else 0
        },
        duration_ms=duration_ms,
        metadata={
            "model": "gpt-4o",
            "answer_word_count": len(answer.split()),
            "tts_summary_word_count": len(tts_summary.split()) if tts_summary else 0
        }
    )
    
    return output_data

def _create_tts_summary_with_data(
    full_answer: str, 
    citations: list, 
    rag_results: list,
    web_results: list,
    comparison_table: list,
    max_words: int = 40
) -> str:
    """Create a concise TTS summary with actual product data (prices, ratings, etc.)"""
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).parent.parent.parent.parent))
    from src.voice.tts import create_tts_summary_with_products
    
    # Use the improved version with structured data
    return create_tts_summary_with_products(
        full_answer=full_answer,
        citations=citations,
        rag_results=rag_results,
        web_results=web_results,
        comparison_table=comparison_table,
        max_duration_seconds=15
    )