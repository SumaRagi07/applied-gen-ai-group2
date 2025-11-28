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
    
    # If query was unsafe, return error message
    if not state.get('is_safe', True):
        output_data = {
            "final_answer": f"I cannot process this request. {state.get('safety_reason', 'Content policy violation.')}",
            "citations": [],
            "tts_summary": None
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
    
    # Limit to top 3 for context size
    rag_summary = json.dumps(rag_results[:3], indent=2) if rag_results else "No results"
    web_summary = json.dumps(web_results[:3], indent=2) if web_results else "No results"
    comparison_summary = json.dumps(comparison_table[:5], indent=2) if comparison_table else "No matches"
    conflicts_summary = json.dumps(conflicts, indent=2) if conflicts else "No conflicts detected"
    
    prompt = SYNTHESIZER_PROMPT.format(
        query=state['user_query'],
        rag_results=rag_summary,
        web_results=web_summary,
        comparison_table=comparison_summary,
        conflicts=conflicts_summary
    )
    
    response = llm.invoke([
        SystemMessage(content="You are a helpful product recommendation assistant."),
        HumanMessage(content=prompt)
    ])
    
    answer = response.content
    
    # Extract citations from answer
    citations = []
    seen_domains = set()
    
    # Extract doc_ids (format: [doc_00123])
    doc_ids = re.findall(r'\[doc_\d+\]', answer)
    citations.extend(doc_ids)
    
    # Extract full URLs in markdown format (format: [text](url))
    urls_markdown = re.findall(r'\]\((https?://[^\)]+)\)', answer)
    for url in urls_markdown:
        # Extract domain from full URL
        domain_match = re.search(r'https?://(?:www\.)?([^/]+)', url)
        if domain_match:
            domain = domain_match.group(1)
            if domain not in seen_domains:
                citations.append(url)
                seen_domains.add(domain)
    
    # Extract URLs in square brackets (format: [https://...])
    urls_brackets = re.findall(r'\[(https?://[^\]]+)\]', answer)
    for url in urls_brackets:
        domain_match = re.search(r'https?://(?:www\.)?([^/]+)', url)
        if domain_match:
            domain = domain_match.group(1)
            if domain not in seen_domains:
                citations.append(url)
                seen_domains.add(domain)
    
    # Extract domain names in brackets (format: [domain.com])
    domains = re.findall(r'\[([a-zA-Z0-9\-]+\.[a-zA-Z0-9\-\.]+)\]', answer)
    for domain in domains:
        # Skip if it's a doc_id or already seen
        if not domain.startswith('doc_') and domain not in seen_domains:
            # Check if we already have a full URL for this domain
            if not any(domain in str(c) for c in citations):
                citations.append(f"[{domain}]")
                seen_domains.add(domain)
    
    print(f"\n[SYNTHESIZER] Generated answer with {len(citations)} unique citations")
    
    # Generate TTS summary (≤15 seconds) with structured product data
    tts_summary = _create_tts_summary_with_data(
        answer, 
        citations, 
        tts_rag_results[:3] if tts_rag_results else [],  # Top 3 products with prices
        tts_web_results[:3] if tts_web_results else [],   # Top 3 web results with prices
        tts_comparison_table[:3] if tts_comparison_table else [],  # Top 3 from comparison
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