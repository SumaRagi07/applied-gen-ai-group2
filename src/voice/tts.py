import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

# Handle both old and new OpenAI API versions
try:
    from openai import OpenAI
    OPENAI_NEW_API = True
except ImportError:
    OPENAI_NEW_API = False
    import openai as openai_old

def text_to_speech(
    text: str,
    output_path: str = "response.mp3",
    voice: str = "alloy",
    model: str = "tts-1",
    speed: float= 1.15
) -> str:
    """
    Convert text to speech using OpenAI TTS API
    
    Args:
        text: Text to convert to speech
        output_path: Where to save audio file (default: response.mp3)
        voice: Voice to use (alloy, echo, fable, onyx, nova, shimmer)
        model: TTS model (tts-1 for speed, tts-1-hd for quality)
        
    Returns:
        str: Path to generated audio file
    """
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("[TTS] Error: OPENAI_API_KEY not set")
        return ""
    
    try:
        if OPENAI_NEW_API:
            # New API (v1.0+)
            client = OpenAI(api_key=api_key)
            print(f"[TTS] Generating speech... (voice: {voice})")
            response = client.audio.speech.create(
                model=model,
                voice=voice,
                input=text, 
                speed=speed
            )
            response.stream_to_file(output_path)
        else:
            # Old API (v0.x) - requires upgrade
            raise ImportError(
                "Your openai package is too old (v0.27.8). "
                "Please upgrade: pip install --upgrade 'openai>=1.0.0'"
            )
        
        print(f"[TTS] Saved audio to {output_path}")
        return output_path
        
    except Exception as e:
        print(f"[TTS] Error: {str(e)}")
        return ""


def get_available_voices():
    """Returns list of available TTS voices"""
    return ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]


# Voice descriptions for choosing
VOICE_INFO = {
    "alloy": "Neutral, clear (recommended for general use)",
    "echo": "Calm, professional",
    "fable": "Expressive, storytelling",
    "onyx": "Deep, authoritative",
    "nova": "Energetic, friendly",
    "shimmer": "Warm, conversational"
}

def create_tts_summary_with_products(
    full_answer: str,
    citations: list = None,
    rag_results: list = None,
    web_results: list = None,
    comparison_table: list = None,
    max_duration_seconds: int = 15
) -> str:
    """Create TTS summary - handles catalog, web-only, or hybrid scenarios"""
    import os
    from langchain_openai import ChatOpenAI
    from langchain_core.messages import SystemMessage, HumanMessage
    
    target_words = max_duration_seconds * 3  # ✅ Increased from 2.5 to 3
    
    products_info = []
    has_catalog_items = False
    has_web_only_items = False
    
    # Process comparison table
    if comparison_table:
        for item in comparison_table[:3]:
            catalog_price = item.get('catalog_price')
            web_price = item.get('web_price')
            title = item.get('title', '')
            source = item.get('web_source', '')
            item_type = item.get('type', '')
            
            # Case 1: Has catalog price
            if catalog_price:
                has_catalog_items = True
                product_text = f"{title} at ${catalog_price:.2f} from our catalog"
                
                # Add web price if significantly different
                if web_price and abs(web_price - catalog_price) > 1:
                    source_clean = source.split(' -')[0].strip() if source else "online"
                    product_text += f", currently ${web_price:.2f} at {source_clean}"
                
                products_info.append(product_text)
            
            # Case 2: Web-only items
            elif web_price and item_type == 'web_only':
                has_web_only_items = True
                source_clean = source.split(' -')[0].strip() if source else "online"
                product_text = f"{title} at ${web_price:.2f} from {source_clean}"
                products_info.append(product_text)
    
    # Fallback to RAG
    if not products_info and rag_results:
        has_catalog_items = True
        for product in rag_results[:3]:
            if product.get('price') and product.get('title'):
                products_info.append(f"{product['title']} at ${product['price']:.2f} from our catalog")
    
    # Fallback to web
    if not products_info and web_results:
        has_web_only_items = True
        for product in web_results[:3]:
            if product.get('price') and product.get('title'):
                source = product.get('source', 'online')
                price_str = product['price'].replace('$', '')
                try:
                    price = float(price_str.replace(',', ''))
                    products_info.append(f"{product['title']} at ${price:.2f} from {source}")
                except:
                    products_info.append(f"{product['title']} from {source}")
    
    # No results
    if not products_info:
        return "I couldn't find any matching products. Try a different search."
    
    products_text = "\n".join(f"{i+1}. {p}" for i, p in enumerate(products_info))
    
    # ✅ DEBUG: Print what we're sending
    print(f"\n[TTS DEBUG] has_catalog_items: {has_catalog_items}, has_web_only_items: {has_web_only_items}")
    print(f"[TTS DEBUG] Products for voice:\n{products_text}\n")
    
    # ✅ FIX: Choose correct intro based on what we actually have
    if has_catalog_items and has_web_only_items:
        start_phrase = "From our catalog and online, my top pick is"
    elif has_catalog_items and not has_web_only_items:
        start_phrase = "From our catalog, my top pick is"
    elif has_web_only_items and not has_catalog_items:
        start_phrase = "My top pick online is"
    else:
        start_phrase = "My top pick is"
    
    prompt = f"""Create a natural voice summary (~{target_words} words, {max_duration_seconds} seconds).

Products with prices:
{products_text}

CRITICAL RULES:
1. Start: "{start_phrase} [Product Name] at [PRICE]."
2. **IF product shows "currently $X at Store", YOU MUST include this price update**
3. Mention 1-2 other options with prices
4. End: "See full details on screen."
5. NO citations, NO markdown
6. Maximum {target_words} words

Example for catalog items:
"From our catalog, my top pick is the Green Toys Puzzle at $10.31, currently $21.99 at Walmart. I also found the Eurographics Puzzle at $18.55. See details on screen."

Example for web-only items:
"My top pick online is CeraVe Cream Moisturizing at $5.99 from Target. I also found Neutrogena Hydro Boost Gel Cream at $9.99 from Target. See details on screen."

Generate (include current prices if shown):"""

    try:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return _simple_fallback_smart(products_info, has_catalog_items, has_web_only_items)
        
        llm = ChatOpenAI(model="gpt-4o", temperature=0.3, api_key=api_key)
        
        response = llm.invoke([
            SystemMessage(content="Create natural voice summaries. ALWAYS use the correct intro phrase provided. Include current prices when provided."),
            HumanMessage(content=prompt)
        ])
        
        summary = response.content.strip()
        summary = _clean_for_tts(summary)
        
        # ✅ REMOVED: Don't force "from our catalog" - LLM uses correct phrase from prompt
        
        return summary
        
    except Exception as e:
        print(f"[TTS] Error: {e}")
        return _simple_fallback_smart(products_info, has_catalog_items, has_web_only_items)

def _simple_fallback_smart(products_info: list, has_catalog: bool, has_web_only: bool = False) -> str:
    """Smart fallback based on what we have"""
    if not products_info:
        return "I couldn't find any matching products. Try a different search."
    
    # ✅ FIX: Choose correct intro
    if has_catalog and has_web_only:
        summary = f"From our catalog and online, my top pick is {products_info[0]}."
    elif has_catalog:
        summary = f"From our catalog, my top pick is {products_info[0]}."
    elif has_web_only:
        summary = f"My top pick online is {products_info[0]}."
    else:
        summary = f"My top pick is {products_info[0]}."
    
    if len(products_info) > 1:
        summary += f" I also found {products_info[1]}."
    
    summary += " See details on screen."
    return summary


def _clean_for_tts(text: str) -> str:
    """Clean text for TTS: remove markdown, fix spacing"""
    import re
    
    # Remove markdown bold/italic
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
    text = re.sub(r'\*([^*]+)\*', r'\1', text)
    text = re.sub(r'__([^_]+)__', r'\1', text)
    text = re.sub(r'_([^_]+)_', r'\1', text)
    
    # Remove citations
    text = re.sub(r'\[doc_\d+\]', '', text)
    text = re.sub(r'\[[a-zA-Z0-9\-\.]+\]', '', text)
    
    # Fix spacing
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'\s+([.,!?])', r'\1', text)
    text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)
    
    # Clean up markdown links
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
    
    return text.strip()


def create_tts_summary(full_answer: str, citations: list = None, max_duration_seconds: int = 15) -> str:
    """Legacy function - kept for compatibility"""
    return _truncate_answer_simple(full_answer, max_duration_seconds * 2, citations)


def _truncate_answer_simple(text: str, max_words: int, citations: list = None) -> str:
    """Simple truncation fallback"""
    text = _clean_for_tts(text)
    words = text.split()
    
    if len(words) <= max_words:
        return text
    else:
        truncated = ' '.join(words[:max_words-5])
        return truncated + "... See details on screen."


def text_to_speech_with_summary(
    full_answer: str,
    citations: list = None,
    output_path: str = "response.mp3",
    voice: str = "alloy",
    model: str = "tts-1",
    max_duration_seconds: int = 15
) -> str:
    """Generate TTS from summary"""
    summary = create_tts_summary(full_answer, citations, max_duration_seconds)
    return text_to_speech(summary, output_path, voice, model)