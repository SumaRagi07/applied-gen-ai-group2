"""
Test script to demonstrate reconciliation logic
Shows how RAG and Web results are matched and conflicts are detected
"""

import sys
sys.path.append('.')

from src.agents.nodes.reconciler import reconciler_node

def test_reconciliation():
    """Test reconciliation with sample data"""
    
    # Sample RAG results (from catalog)
    rag_results = [
        {
            "doc_id": "doc_00123",
            "title": "Melissa & Doug Wooden Jigsaw Puzzle",
            "price": 12.99,
            "brand": "Melissa & Doug",
            "main_category": "Toys",
            "eco_friendly": True,
            "relevance_score": 0.95
        },
        {
            "doc_id": "doc_00456",
            "title": "Eco-Friendly Wooden Building Blocks",
            "price": 18.50,
            "brand": "Green Toys",
            "main_category": "Toys",
            "eco_friendly": True,
            "relevance_score": 0.88
        },
        {
            "doc_id": "doc_00789",
            "title": "Classic Wooden Puzzle Set",
            "price": 15.00,
            "brand": "Plan Toys",
            "main_category": "Toys",
            "eco_friendly": True,
            "relevance_score": 0.82
        }
    ]
    
    # Sample Web results (current)
    web_results = [
        {
            "title": "Melissa & Doug Wooden Jigsaw Puzzle - 24 Pieces",
            "url": "https://www.amazon.com/melissa-doug-wooden-puzzle",
            "snippet": "Melissa & Doug Wooden Jigsaw Puzzle for kids. Price: $15.99. Available now.",
            "price": "$15.99",
            "source": "amazon.com"
        },
        {
            "title": "Green Toys Eco-Friendly Building Blocks Set",
            "url": "https://www.target.com/green-toys-blocks",
            "snippet": "Green Toys building blocks made from recycled materials. Price: $19.99",
            "price": "$19.99",
            "source": "target.com"
        },
        {
            "title": "New Wooden Puzzle Game for Children",
            "url": "https://www.walmart.com/new-puzzle-game",
            "snippet": "Latest wooden puzzle game. Price: $12.50",
            "price": "$12.50",
            "source": "walmart.com"
        }
    ]
    
    # Create state
    state = {
        "user_query": "Find eco-friendly wooden puzzles under $20",
        "rag_results": rag_results,
        "web_results": web_results
    }
    
    print("="*70)
    print("RECONCILIATION TEST")
    print("="*70)
    print(f"\nRAG Results (Catalog): {len(rag_results)} products")
    print(f"Web Results (Current): {len(web_results)} products")
    
    # Run reconciliation
    result = reconciler_node(state)
    
    print("\n" + "="*70)
    print("RECONCILIATION RESULTS")
    print("="*70)
    
    print(f"\n✓ Matched Products: {len(result['matched_products'])}")
    for i, match in enumerate(result['matched_products'], 1):
        rag = match['rag_product']
        web = match['web_product']
        print(f"\n  Match {i}:")
        print(f"    Catalog: {rag['title'][:50]}... - ${rag['price']:.2f} [doc_{rag['doc_id'][-5:]}]")
        print(f"    Web:     {web['title'][:50]}... - {web.get('price', 'N/A')} [{web['source']}]")
        print(f"    Similarity: {match['similarity_score']:.1%}")
    
    print(f"\n✓ Conflicts Detected: {len(result['conflicts'])}")
    for i, conflict in enumerate(result['conflicts'], 1):
        print(f"\n  Conflict {i}:")
        print(f"    Product: {conflict['rag_title'][:50]}...")
        for c in conflict['conflicts']:
            print(f"    - {c['message']}")
    
    print(f"\n✓ Comparison Table: {len(result['comparison_table'])} entries")
    print("\n  Comparison Table Preview:")
    print("  " + "-"*66)
    print(f"  {'Title':<30} {'Catalog $':<12} {'Web $':<12} {'Sources':<10}")
    print("  " + "-"*66)
    for entry in result['comparison_table'][:5]:
        title = entry['title'][:28] if entry['title'] else "N/A"
        cat_price = f"${entry['catalog_price']:.2f}" if entry['catalog_price'] else "N/A"
        web_price = entry['web_price'] if entry['web_price'] else "N/A"
        sources = ", ".join(entry['sources'])
        conflict_marker = " ⚠" if entry['has_conflict'] else ""
        print(f"  {title:<30} {cat_price:<12} {web_price:<12} {sources:<10}{conflict_marker}")
    
    print("\n" + "="*70)
    print("TEST COMPLETE")
    print("="*70)
    
    return result

if __name__ == "__main__":
    test_reconciliation()

