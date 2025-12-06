"""
Reconciliation node: Matches and compares RAG (catalog) vs Web results
- Matches products by brand/title similarity
- Detects price conflicts
- Creates unified comparison table
"""

import re
import time
import concurrent.futures  
from typing import List, Dict, Any, Optional
from difflib import SequenceMatcher
from ..utils.logger import get_logger

def _similarity(a: str, b: str) -> float:
    """Calculate string similarity (0-1)"""
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

def _extract_price(price_str: Optional[str]) -> Optional[float]:
    """Extract numeric price from string like '$12.99' or '12.99'"""
    if not price_str:
        return None
    
    # Remove $ and commas, extract number
    price_clean = re.sub(r'[^\d.]', '', str(price_str))
    try:
        return float(price_clean)
    except (ValueError, TypeError):
        return None

def _normalize_brand(brand: str) -> str:
    """Normalize brand name for matching"""
    if not brand:
        return ""
    # Remove common suffixes, lowercase, strip
    normalized = brand.lower().strip()
    # Remove common words
    for word in ['inc', 'llc', 'corp', 'company', 'co']:
        normalized = normalized.replace(f' {word}', '').replace(f'.{word}', '')
    return normalized

def _normalize_title(title: str) -> str:
    """Normalize product title for matching"""
    if not title:
        return ""
    # Lowercase, remove extra spaces, remove common words
    normalized = title.lower().strip()
    # Remove common product words that don't help matching
    stopwords = ['the', 'a', 'an', 'for', 'with', 'and', 'or']
    words = normalized.split()
    words = [w for w in words if w not in stopwords]
    return ' '.join(words)

import concurrent.futures

def _find_best_match_for_product(rag_product: Dict, web_results: List[Dict], used_indices: set) -> Optional[Dict]:
    """Find best web match for a single RAG product (parallelizable)"""
    best_match = None
    best_score = 0.0
    best_web_idx = None
    
    rag_brand = _normalize_brand(rag_product.get('brand', ''))
    rag_title = _normalize_title(rag_product.get('title', ''))
    
    for web_idx, web_product in enumerate(web_results):
        if web_idx in used_indices:
            continue
        
        # Extract brand from web title/snippet (simple heuristic)
        web_title = _normalize_title(web_product.get('title', ''))
        web_snippet = web_product.get('snippet', '').lower()
        
        # Try to extract brand from web result
        web_title_words = web_title.split()[:3]
        web_brand_candidates = ' '.join(web_title_words)
        
        # Calculate brand similarity
        brand_sim = _similarity(rag_brand, web_brand_candidates) if rag_brand else 0.0
        
        # Calculate title similarity
        title_sim = _similarity(rag_title, web_title)
        
        # Combined score (weighted: brand 40%, title 60%)
        combined_score = (brand_sim * 0.4) + (title_sim * 0.6)
        
        # Also check if brand appears in snippet
        if rag_brand and rag_brand in web_snippet:
            combined_score += 0.2
            combined_score = min(combined_score, 1.0)
        
        if combined_score > best_score and combined_score > 0.5:
            best_score = combined_score
            best_match = web_product
            best_web_idx = web_idx
    
    if best_match:
        return {
            'rag_product': rag_product,
            'web_product': best_match,
            'web_idx': best_web_idx,
            'similarity_score': round(best_score, 3),
            'match_type': 'brand_title' if best_score > 0.7 else 'partial'
        }
    return None


def _match_products(rag_results: List[Dict], web_results: List[Dict]) -> List[Dict]:
    """
    Match RAG products with Web products USING PARALLELIZATION
    
    Returns list of matched pairs with similarity scores
    """
    matched_pairs = []
    used_web_indices = set()
    
    # ✅ PARALLEL MATCHING - Process all RAG products simultaneously
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        # Submit all matching tasks
        futures = {
            executor.submit(_find_best_match_for_product, rag_product, web_results, used_web_indices): rag_product
            for rag_product in rag_results
        }
        
        # Collect results as they complete
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            if result:
                # Mark web index as used
                used_web_indices.add(result['web_idx'])
                # Remove the web_idx from result before appending
                web_idx = result.pop('web_idx')
                matched_pairs.append(result)
    
    return matched_pairs

def _detect_conflicts(matched_pairs: List[Dict]) -> List[Dict]:
    """
    Detect conflicts between matched products (price discrepancies, etc.)
    """
    conflicts = []
    
    for pair in matched_pairs:
        rag_product = pair['rag_product']
        web_product = pair['web_product']
        
        rag_price = rag_product.get('price')
        web_price_str = web_product.get('price')
        web_price = _extract_price(web_price_str)
        
        conflict = {
            'rag_product_id': rag_product.get('doc_id'),
            'rag_title': rag_product.get('title'),
            'web_url': web_product.get('url'),
            'web_title': web_product.get('title'),
            'conflicts': []
        }
        
        # Price conflict
        if rag_price and web_price:
            price_diff = abs(rag_price - web_price)
            price_diff_pct = (price_diff / rag_price) * 100 if rag_price > 0 else 0
            
            # Flag if price difference > 20% or > $5
            if price_diff_pct > 20 or price_diff > 5.0:
                conflict['conflicts'].append({
                    'type': 'price_discrepancy',
                    'rag_price': rag_price,
                    'web_price': web_price,
                    'difference': round(price_diff, 2),
                    'difference_pct': round(price_diff_pct, 1),
                    'message': f"Catalog shows ${rag_price:.2f}, web shows ${web_price:.2f} ({price_diff_pct:.1f}% difference)"
                })
        
        if conflict['conflicts']:
            conflicts.append(conflict)
    
    return conflicts

def _create_comparison_table(rag_results: List[Dict], web_results: List[Dict], matched_pairs: List[Dict]) -> List[Dict]:
    """
    Create unified comparison table combining RAG and Web results
    """
    comparison = []
    
    # Add matched products (with both sources)
    for pair in matched_pairs:
        rag = pair['rag_product']
        web = pair['web_product']
        
        rag_price = rag.get('price')
        web_price = _extract_price(web.get('price'))
        
        comparison.append({
            'title': rag.get('title'),
            'brand': rag.get('brand'),
            'catalog_price': rag_price,
            'web_price': web_price,
            'catalog_id': rag.get('doc_id'),
            'web_url': web.get('url'),
            'web_source': web.get('source'),
            'image_url': rag.get('image_url'),  # Use catalog image
            'product_url': rag.get('product_url'),
            'eco_friendly': rag.get('eco_friendly'),
            'rating': web.get('rating'),  # ✅ Add web rating
            'reviews': web.get('reviews'),  # ✅ Add web reviews
            'match_confidence': pair['similarity_score'],
            'has_conflict': len([c for c in _detect_conflicts([pair]) if c['conflicts']]) > 0,
            'sources': ['catalog', 'web'],
            'type': 'matched'
        })
    
    # Add unmatched RAG products (catalog only)
    matched_rag_ids = {pair['rag_product'].get('doc_id') for pair in matched_pairs}
    for rag_product in rag_results:
        if rag_product.get('doc_id') not in matched_rag_ids:
            comparison.append({
                'title': rag_product.get('title'),
                'brand': rag_product.get('brand'),
                'catalog_price': rag_product.get('price'),
                'web_price': None,
                'catalog_id': rag_product.get('doc_id'),
                'web_url': None,
                'web_source': None,
                'image_url': rag_product.get('image_url'),
                'product_url': rag_product.get('product_url'),
                'eco_friendly': rag_product.get('eco_friendly'),
                'rating': None,
                'reviews': None,
                'match_confidence': None,
                'has_conflict': False,
                'sources': ['catalog'],
                'type': 'catalog_only'
            })
    
    # Add unmatched web products (web only) - ✅ USE WEB THUMBNAIL
    matched_web_urls = {pair['web_product'].get('url') for pair in matched_pairs}
    for web_product in web_results:
        if web_product.get('url') not in matched_web_urls:
            web_price = _extract_price(web_product.get('price'))
            comparison.append({
                'title': web_product.get('title'),
                'brand': None,
                'catalog_price': None,
                'web_price': web_price,
                'catalog_id': None,
                'web_url': web_product.get('url'),
                'web_source': web_product.get('source'),
                'image_url': web_product.get('thumbnail'),  # ✅ USE WEB THUMBNAIL
                'product_url': web_product.get('url'),
                'eco_friendly': None,
                'rating': web_product.get('rating'),  # ✅ Add web rating
                'reviews': web_product.get('reviews'),  # ✅ Add web reviews
                'match_confidence': None,
                'has_conflict': False,
                'sources': ['web'],
                'type': 'web_only'
            })
    
    return comparison

def reconciler_node(state):
    """
    Reconcile RAG and Web search results:
    - Match products by brand/title similarity
    - Detect conflicts (price discrepancies)
    - Create unified comparison table
    """
    start_time = time.time()
    logger = get_logger()
    
    rag_results = state.get('rag_results', []) or []
    web_results = state.get('web_results', []) or []
    
    input_data = {
        "rag_count": len(rag_results),
        "web_count": len(web_results)
    }
    
    print(f"\n[RECONCILER] Starting reconciliation...")
    print(f"[RECONCILER] RAG results: {len(rag_results)}, Web results: {len(web_results)}")
    
    # If no web results, skip reconciliation
    if not web_results:
        print("[RECONCILER] No web results to reconcile")
        output_data = {
            "matched_products": [],
            "conflicts": [],
            "comparison_table": [
                {
                    'title': r.get('title'),
                    'brand': r.get('brand'),
                    'catalog_price': r.get('price'),
                    'web_price': None,
                    'catalog_id': r.get('doc_id'),
                    'web_url': None,
                    'web_source': None,
                    'image_url': r.get('image_url'),
                    'product_url': r.get('product_url'),
                    'eco_friendly': r.get('eco_friendly'),
                    'rating': None,
                    'reviews': None,
                    'match_confidence': None,
                    'has_conflict': False,
                    'sources': ['catalog'],
                    'type': 'catalog_only'
                }
                for r in rag_results
            ]
        }
        duration_ms = (time.time() - start_time) * 1000
        logger.log_step(
            node_name="reconciler",
            input_data=input_data,
            output_data={"matched_count": 0, "conflicts_count": 0, "comparison_table_count": len(output_data['comparison_table'])},
            duration_ms=duration_ms,
            metadata={"reason": "No web results"}
        )
        return output_data
    
    # If no RAG results, return web-only comparison
    if not rag_results:
        print("[RECONCILER] No RAG results to reconcile")
        output_data = {
            "matched_products": [],
            "conflicts": [],
            "comparison_table": [
                {
                    'title': w.get('title'),
                    'brand': None,
                    'catalog_price': None,
                    'web_price': _extract_price(w.get('price')),
                    'catalog_id': None,
                    'web_url': w.get('url'),
                    'web_source': w.get('source'),
                    'image_url': w.get('thumbnail'),  # ✅ USE WEB THUMBNAIL
                    'product_url': w.get('url'),
                    'eco_friendly': None,
                    'rating': w.get('rating'),
                    'reviews': w.get('reviews'),
                    'match_confidence': None,
                    'has_conflict': False,
                    'sources': ['web'],
                    'type': 'web_only'
                }
                for w in web_results
            ]
        }
        duration_ms = (time.time() - start_time) * 1000
        logger.log_step(
            node_name="reconciler",
            input_data=input_data,
            output_data={"matched_count": 0, "conflicts_count": 0, "comparison_table_count": len(output_data['comparison_table'])},
            duration_ms=duration_ms,
            metadata={"reason": "No RAG results"}
        )
        return output_data
    
    # Match products
    matched_pairs = _match_products(rag_results, web_results)
    print(f"[RECONCILER] Matched {len(matched_pairs)} products")
    
    # Detect conflicts
    conflicts = _detect_conflicts(matched_pairs)
    print(f"[RECONCILER] Found {len(conflicts)} conflicts")
    
    # Create comparison table
    comparison_table = _create_comparison_table(rag_results, web_results, matched_pairs)
    print(f"[RECONCILER] Created comparison table with {len(comparison_table)} entries")
    
    # Log some examples
    if matched_pairs:
        example = matched_pairs[0]
        print(f"[RECONCILER] Example match: '{example['rag_product'].get('title', '')[:50]}...' "
              f"<-> '{example['web_product'].get('title', '')[:50]}...' "
              f"(score: {example['similarity_score']})")
    
    if conflicts:
        example_conflict = conflicts[0]
        print(f"[RECONCILER] Example conflict: {example_conflict['conflicts'][0]['message']}")
    
    output_data = {
        "matched_products": matched_pairs,
        "conflicts": conflicts,
        "comparison_table": comparison_table
    }
    duration_ms = (time.time() - start_time) * 1000
    
    # Log step
    logger.log_step(
        node_name="reconciler",
        input_data=input_data,
        output_data={
            "matched_count": len(matched_pairs),
            "conflicts_count": len(conflicts),
            "comparison_table_count": len(comparison_table)
        },
        duration_ms=duration_ms,
        metadata={
            "matched_pairs": len(matched_pairs),
            "conflicts": len(conflicts),
            "example_match_score": matched_pairs[0]['similarity_score'] if matched_pairs else None
        }
    )
    
    return output_data