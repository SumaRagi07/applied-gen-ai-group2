import json
import os
import re
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from ..prompts import SYNTHESIZER_PROMPT

load_dotenv()

def synthesizer_node(state):
    """Generate final answer with citations"""
    
    # If query was unsafe, return error message
    if not state.get('is_safe', True):
        return {
            "final_answer": f"I cannot process this request. {state.get('safety_reason', 'Content policy violation.')}",
            "citations": []
        }
    
    llm = ChatOpenAI(
        model="gpt-4o", 
        temperature=0.3,
        api_key=os.getenv("OPENAI_API_KEY")
    )
    
    # Format results for prompt
    rag_results = state.get('rag_results', [])
    web_results = state.get('web_results', [])
    
    # Limit to top 3 for context size
    rag_summary = json.dumps(rag_results[:3], indent=2) if rag_results else "No results"
    web_summary = json.dumps(web_results[:3], indent=2) if web_results else "No results"
    
    prompt = SYNTHESIZER_PROMPT.format(
        query=state['user_query'],
        rag_results=rag_summary,
        web_results=web_summary
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
    
    return {
        "final_answer": answer,
        "citations": citations
    }