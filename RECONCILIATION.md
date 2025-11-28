# Product Reconciliation Logic

## Overview

The reconciliation node (`src/agents/nodes/reconciler.py`) matches products from the private catalog (RAG results) with current web search results, detects conflicts, and creates a unified comparison table.

## How It Works

### 1. Product Matching

Products are matched using fuzzy string similarity on:
- **Brand names** (40% weight): Normalized brand extraction and comparison
- **Product titles** (60% weight): Normalized title comparison
- **Snippet matching** (+20% bonus): If brand appears in web snippet

**Matching Algorithm:**
- Uses `SequenceMatcher` for string similarity (0-1 scale)
- Minimum threshold: 50% similarity required for a match
- Prevents duplicate matches (each web result matches at most one catalog product)

### 2. Conflict Detection

Conflicts are detected when:
- **Price discrepancies**: Difference > 20% OR > $5.00
  - Example: Catalog shows $12.99, web shows $15.99 (23% difference) → Conflict flagged

### 3. Comparison Table

Creates a unified table with three types of entries:

1. **Matched Products** (found in both catalog and web):
   - Shows both prices
   - Includes match confidence score
   - Flags conflicts if detected
   - Sources: `['catalog', 'web']`

2. **Catalog-Only Products** (in catalog but not found on web):
   - Shows catalog price only
   - Sources: `['catalog']`

3. **Web-Only Products** (found on web but not in catalog):
   - Shows web price only
   - Sources: `['web']`

## Integration with LangGraph

The reconciler node is inserted between the Executor and Synthesizer:

```
Router → Safety → Planner → Executor → **Reconciler** → Synthesizer → END
```

**State Updates:**
- `matched_products`: List of matched pairs with similarity scores
- `conflicts`: List of detected conflicts with details
- `comparison_table`: Unified table for display/synthesis

## Usage Example

```python
from src.agents.nodes.reconciler import reconciler_node

state = {
    "rag_results": [...],  # From catalog
    "web_results": [...]    # From web search
}

result = reconciler_node(state)

# Access results:
matched = result['matched_products']
conflicts = result['conflicts']
comparison = result['comparison_table']
```

## Output Format

### Matched Products
```python
{
    'rag_product': {...},      # Catalog product dict
    'web_product': {...},       # Web product dict
    'similarity_score': 0.85,   # 0-1 match confidence
    'match_type': 'brand_title' # or 'partial'
}
```

### Conflicts
```python
{
    'rag_product_id': 'doc_00123',
    'rag_title': 'Product Name',
    'web_url': 'https://...',
    'web_title': 'Product Name',
    'conflicts': [
        {
            'type': 'price_discrepancy',
            'rag_price': 12.99,
            'web_price': 15.99,
            'difference': 3.00,
            'difference_pct': 23.1,
            'message': 'Catalog shows $12.99, web shows $15.99 (23.1% difference)'
        }
    ]
}
```

### Comparison Table Entry
```python
{
    'title': 'Product Name',
    'brand': 'Brand Name',
    'catalog_price': 12.99,
    'web_price': 15.99,
    'catalog_id': 'doc_00123',
    'web_url': 'https://...',
    'web_source': 'amazon.com',
    'match_confidence': 0.85,
    'has_conflict': True,
    'sources': ['catalog', 'web']
}
```

## Testing

Run the test script to see reconciliation in action:

```bash
python test_reconciliation.py
```

This demonstrates:
- Product matching by brand/title
- Conflict detection (price discrepancies)
- Comparison table generation
- Handling of unmatched products

## Edge Cases Handled

1. **No web results**: Returns catalog-only comparison table
2. **No RAG results**: Returns web-only comparison table
3. **No matches**: Returns separate entries for all products
4. **Price extraction**: Handles various formats ($12.99, 12.99, "$12.99 USD")
5. **Brand normalization**: Removes common suffixes (Inc, LLC, Corp)
6. **Title normalization**: Removes stopwords for better matching

## Future Enhancements

Potential improvements:
- SKU/barcode matching for exact product identification
- Availability conflict detection (out of stock, discontinued)
- Rating/review comparison
- Image-based matching (visual similarity)
- Multi-source price aggregation (average across retailers)

