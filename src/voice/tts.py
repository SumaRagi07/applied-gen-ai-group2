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
    model: str = "tts-1"
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
        
    Example:
        >>> audio = text_to_speech("Hello, how can I help you?")
        >>> # Now play audio file
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
                input=text
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
    """
    Returns list of available TTS voices
    
    Returns:
        list: Available voice names
    """
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
    """
    Create a concise TTS summary with structured product data (prices, ratings, etc.)
    
    Args:
        full_answer: The complete answer text
        citations: List of citations
        rag_results: List of RAG product results with prices
        web_results: List of web product results with prices
        comparison_table: Comparison table with matched products
        max_duration_seconds: Maximum speech duration (default: 15)
        
    Returns:
        str: Concise summary text with actual prices and product details
    """
    import os
    from langchain_openai import ChatOpenAI
    from langchain_core.messages import SystemMessage, HumanMessage
    
    # Estimate word count for target duration (conservative: 2 words/second)
    target_words = max_duration_seconds * 2
    
    # Build structured product data for the prompt
    products_data = []
    
    # Use comparison table if available (has matched products with prices)
    if comparison_table:
        for item in comparison_table[:3]:  # Top 3
            product_info = {
                "title": item.get('title', ''),
                "catalog_price": item.get('catalog_price'),
                "web_price": item.get('web_price'),
                "source": "matched" if item.get('type') == 'matched' else item.get('type', 'unknown')
            }
            if product_info['catalog_price'] or product_info['web_price']:
                products_data.append(product_info)
    
    # Fallback to RAG/web results if no comparison table
    if not products_data and rag_results:
        for product in rag_results[:3]:
            products_data.append({
                "title": product.get('title', ''),
                "catalog_price": product.get('price'),
                "web_price": None,
                "source": "catalog"
            })
    
    if not products_data and web_results:
        for product in web_results[:3]:
            products_data.append({
                "title": product.get('title', ''),
                "catalog_price": None,
                "web_price": product.get('price'),
                "source": "web"
            })
    
    # Format products for prompt
    products_text = ""
    if products_data:
        products_text = "\n\nStructured Product Data (use actual prices from here):\n"
        for i, prod in enumerate(products_data, 1):
            price_info = []
            if prod['catalog_price']:
                price_info.append(f"Catalog: ${prod['catalog_price']}")
            if prod['web_price']:
                price_info.append(f"Current: ${prod['web_price']}")
            
            products_text += f"{i}. {prod['title']}\n"
            if price_info:
                products_text += f"   Price: {', '.join(price_info)}\n"
            products_text += f"   Source: {prod['source']}\n\n"
    
    citations_text = ""
    if citations:
        citations_text = f"\n\nCitations to include: {', '.join(citations[:3])}"
    
    summary_prompt = f"""Create a natural, conversational voice summary (≤{target_words} words, ~{max_duration_seconds} seconds) for a product recommendation assistant.

Full answer text:
{full_answer}
{products_text}
{citations_text}

CRITICAL REQUIREMENTS - Follow this EXACT format:
1. Start with: "Here are [number] options that fit your [criteria]."
2. Then IMMEDIATELY say: "My top pick is [Product Name]"
3. After product name, add: —[feature], [rating if available], typically $[ACTUAL PRICE from Structured Product Data]
4. If multiple products: "I compared this with [number] alternatives."
5. End with: "I've sent details and sources to your screen. Would you like the most affordable or the highest rated?"

Example (copy this structure exactly):
"Here are three options that fit your budget and material. My top pick is Brand X Steel-Safe Eco Cleaner—plant-based surfactants, 4.6 star average rating, typically $12.49. I compared this with two alternatives. I've sent details and sources to your screen. Would you like the most affordable or the highest rated?"

Rules:
- MUST use the exact phrase "My top pick is" (not "top choice" or "best option")
- Use ACTUAL PRICES from Structured Product Data above (never "$X.XX" placeholders)
- Product names: proper spacing, use dashes for readability
- Features: mention one key benefit (eco-friendly, plant-based, rating, etc.)
- Use em-dash (—) or comma before features
- Use "typically" or "around" before price
- NO markdown (no **, no [], no special characters)
- Maximum {target_words} words
- Natural, conversational tone

Generate the summary now (must include "My top pick is"):"""

    try:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            # Fallback: simple truncation
            return _truncate_answer_simple(full_answer, target_words, citations)
        
        llm = ChatOpenAI(
            model="gpt-4o",
            temperature=0.4,  # Slightly higher for more natural conversation
            api_key=api_key
        )
        
        response = llm.invoke([
            SystemMessage(content="You are creating a natural, conversational voice summary for a product recommendation assistant. Always use actual prices from the provided data, never placeholders. You MUST include the exact phrase 'My top pick is' in your response."),
            HumanMessage(content=summary_prompt)
        ])
        
        summary = response.content.strip()
        
        # Ensure "My top pick" is ALWAYS included (add if missing)
        if "my top pick" not in summary.lower():
            import re
            # Pattern 1: "Here are X options that fit..." -> "Here are X options that fit... My top pick is"
            summary = re.sub(
                r'(Here (is|are) (?:some |\d+ |three |two |one )?[^:]*?options?[^:]*?)([:])',
                r'\1. My top pick is',
                summary,
                flags=re.IGNORECASE
            )
            # Pattern 2: "Here is/are" at start -> "My top pick is" (only if no product name follows)
            if "my top pick" not in summary.lower():
                # Check if there's a product name right after "Here is/are"
                match = re.match(r'^(Here (is|are)) (.+)$', summary, re.IGNORECASE)
                if match:
                    intro, rest = match.group(1), match.group(3)
                    # If rest starts with a product name (capitalized), insert "My top pick is" before product
                    product_match = re.match(r'^([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,})', rest)
                    if product_match:
                        summary = f"My top pick is {rest}"
                    else:
                        summary = f"My top pick is {rest}"
                else:
                    summary = "My top pick is " + summary
        
        # Clean up markdown and formatting for TTS
        summary = _clean_for_tts(summary)
        
        # Verify word count
        summary_words = len(summary.split())
        if summary_words > target_words * 1.2:  # Allow 20% overage
            # Fallback to simple truncation if too long
            return _truncate_answer_simple(full_answer, target_words, citations)
        
        return summary
        
    except Exception as e:
        print(f"[TTS] Error creating summary: {e}, using simple truncation")
        return _truncate_answer_simple(full_answer, target_words, citations)


def create_tts_summary(full_answer: str, citations: list = None, max_duration_seconds: int = 15) -> str:
    """
    Create a concise summary suitable for TTS (≤15 seconds)
    
    Args:
        full_answer: The complete answer text
        citations: List of citations to preserve
        max_duration_seconds: Maximum speech duration (default: 15)
        
    Returns:
        str: Concise summary text (approximately max_duration_seconds of speech)
        
    Note:
        Average speech rate: ~150 words per minute = 2.5 words/second
        15 seconds ≈ 37-40 words
    """
    import os
    from langchain_openai import ChatOpenAI
    from langchain_core.messages import SystemMessage, HumanMessage
    
    # Estimate word count for target duration (conservative: 2 words/second)
    target_words = max_duration_seconds * 2
    
    # If answer is already short enough, return as-is
    word_count = len(full_answer.split())
    if word_count <= target_words:
        return full_answer
    
    # Create summary prompt
    citations_text = ""
    if citations:
        citations_text = f"\n\nCitations to include: {', '.join(citations[:3])}"  # Top 3 citations
    
    summary_prompt = f"""Create a concise voice summary (≤{target_words} words, ~{max_duration_seconds} seconds of speech) from this product recommendation answer.

Full answer:
{full_answer}
{citations_text}

Requirements:
- Keep it natural and conversational for TEXT-TO-SPEECH
- Include the top 1-2 product recommendations with prices
- Format product names clearly with proper spacing (e.g., "Krumbs Kitchen Chef's Collection Silicone Turner, Green" not "Krumbs KitchenChef'sCollectionSiliconeTurner")
- Mention key features or benefits briefly
- For citations, use natural spoken format:
  * Instead of "[doc_04447]", say "from document 04447" or "catalog entry 04447"
  * Instead of "[amazon.com]", say "from Amazon" or "on Amazon"
- DO NOT include markdown formatting (no **, no [], no special characters that don't read well)
- End with a brief note about checking the full details on screen
- Maximum {target_words} words
- Ensure proper spacing between words and phrases

Generate the summary (plain text, no markdown):"""

    try:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            # Fallback: simple truncation
            return _truncate_answer_simple(full_answer, target_words, citations)
        
        llm = ChatOpenAI(
            model="gpt-4o",
            temperature=0.3,
            api_key=api_key
        )
        
        response = llm.invoke([
            SystemMessage(content="You are creating a concise voice summary for text-to-speech."),
            HumanMessage(content=summary_prompt)
        ])
        
        summary = response.content.strip()
        
        # Clean up markdown and formatting for TTS
        summary = _clean_for_tts(summary)
        
        # Verify word count
        summary_words = len(summary.split())
        if summary_words > target_words * 1.2:  # Allow 20% overage
            # Fallback to simple truncation if too long
            return _truncate_answer_simple(full_answer, target_words, citations)
        
        return summary
        
    except Exception as e:
        print(f"[TTS] Error creating summary: {e}, using simple truncation")
        return _truncate_answer_simple(full_answer, target_words, citations)


def _clean_for_tts(text: str) -> str:
    """Clean text for TTS: remove markdown, fix spacing, convert citations to natural speech"""
    import re
    
    # Remove markdown bold/italic
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)  # **text** -> text
    text = re.sub(r'\*([^*]+)\*', r'\1', text)      # *text* -> text
    text = re.sub(r'__([^_]+)__', r'\1', text)      # __text__ -> text
    text = re.sub(r'_([^_]+)_', r'\1', text)        # _text_ -> text
    
    # Convert citation formats to natural speech
    # [doc_04447] -> "from document 04447" or "catalog entry 04447"
    text = re.sub(r'\[doc_(\d+)\]', r'from document \1', text)
    
    # [amazon.com] or [domain.com] -> "from Amazon" or "from domain"
    text = re.sub(r'\[([a-zA-Z0-9\-]+)\.([a-zA-Z0-9\-\.]+)\]', 
                  lambda m: f"from {m.group(1).capitalize()}" if m.group(1) in ['amazon', 'walmart', 'target', 'ebay'] 
                  else f"from {m.group(1)}", text)
    
    # Fix spacing issues (multiple spaces, missing spaces before punctuation)
    text = re.sub(r'\s+', ' ', text)  # Multiple spaces -> single space
    text = re.sub(r'\s+([.,!?])', r'\1', text)  # Space before punctuation -> no space
    text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)  # Add space between lowercase and uppercase
    
    # Fix common concatenation issues
    text = re.sub(r'([a-z])([A-Z][a-z])', r'\1 \2', text)  # "wordWord" -> "word Word"
    text = re.sub(r'(\d+)([A-Za-z])', r'\1 \2', text)  # "7Toppick" -> "7 Toppick"
    text = re.sub(r'([A-Za-z])(\d+)', r'\1 \2', text)  # "Greenat7" -> "Green at 7"
    
    # Clean up any remaining markdown links [text](url) -> text
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
    
    return text.strip()


def _truncate_answer_simple(text: str, max_words: int, citations: list = None) -> str:
    """Simple fallback: truncate to max_words while preserving citations"""
    # Clean text first
    text = _clean_for_tts(text)
    
    words = text.split()
    
    if len(words) <= max_words:
        result = text
    else:
        # Take first max_words-10 words, then add citation note
        truncated = ' '.join(words[:max_words-10])
        
        if citations:
            citation_note = f" See details and citations on screen."
            truncated += citation_note
        
        result = truncated + "..."
    
    # Ensure "My top pick" is included
    if "my top pick" not in result.lower():
        import re
        # Replace "Here is/are" with "My top pick is"
        result = re.sub(r'^(Here (is|are))', 'My top pick is', result, flags=re.IGNORECASE)
        # If still not found, prepend it
        if "my top pick" not in result.lower():
            result = "My top pick is " + result
    
    return result


def text_to_speech_with_summary(
    full_answer: str,
    citations: list = None,
    output_path: str = "response.mp3",
    voice: str = "alloy",
    model: str = "tts-1",
    max_duration_seconds: int = 15
) -> str:
    """
    Generate TTS from a concise summary (≤15 seconds) of the full answer
    
    Args:
        full_answer: Complete answer text
        citations: List of citations
        output_path: Where to save audio file
        voice: Voice to use
        model: TTS model
        max_duration_seconds: Maximum speech duration (default: 15)
        
    Returns:
        str: Path to generated audio file
    """
    # Create summary
    summary = create_tts_summary(full_answer, citations, max_duration_seconds)
    
    # Generate TTS from summary
    return text_to_speech(summary, output_path, voice, model)