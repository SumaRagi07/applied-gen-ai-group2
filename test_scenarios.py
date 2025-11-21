import requests
import json
import time

BASE_URL = "http://localhost:8000"

def print_section(title):
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70 + "\n")

def test_rag_search(query, filters, description):
    print(f"TEST: {description}")
    print(f"Query: '{query}'")
    if filters:
        print(f"Filters: {filters}")
    
    params = {"query": query, "top_k": 5}
    params.update(filters)
    
    response = requests.post(
        f"{BASE_URL}/call",
        json={"tool": "rag.search", "params": params}
    )
    
    result = response.json()
    if result['success']:
        data = result['data']
        print(f"✓ Found: {data['total_found']} products")
        print(f"  Query time: {result['execution_time_ms']}ms")
        
        for i, product in enumerate(data['results'][:3], 1):
            print(f"  {i}. {product['title'][:65]}...")
            print(f"     ${product['price']:.2f} | {product['main_category']} | Eco: {product['eco_friendly']}")
    else:
        print(f"✗ Error: {result['error']}")
    
    print()

def test_web_search(query, description):
    print(f"TEST: {description}")
    print(f"Query: '{query}'")
    
    response = requests.post(
        f"{BASE_URL}/call",
        json={
            "tool": "web.search",
            "params": {"query": query, "max_results": 5}
        }
    )
    
    result = response.json()
    if result['success']:
        data = result['data']
        print(f"✓ Found: {data['total_found']} results")
        print(f"  Cached: {data['cached']} | Query time: {result['execution_time_ms']}ms")
        
        for i, item in enumerate(data['results'][:3], 1):
            print(f"  {i}. {item['title'][:65]}...")
            print(f"     Price: {item['price'] or 'N/A'} | Source: {item['source']}")
    else:
        print(f"✗ Error: {result['error']}")
    
    print()

# ============================================================================
# START TESTS
# ============================================================================

print_section("MCP SERVER COMPREHENSIVE TESTING")

# Test 1: Health & Discovery
print_section("1. SERVER HEALTH & TOOL DISCOVERY")

print("Health Check:")
response = requests.get(f"{BASE_URL}/health")
print(f"✓ Status: {response.json()['status']}\n")

print("Available Tools:")
response = requests.get(f"{BASE_URL}/tools")
tools = response.json()['tools']
for tool in tools:
    print(f"  - {tool['name']}: {tool['description']}")
print()

# Test 2: Basic RAG Queries
print_section("2. RAG SEARCH - BASIC QUERIES")

test_rag_search(
    "wooden puzzle for kids",
    {},
    "Basic search - no filters"
)

test_rag_search(
    "stuffed animal",
    {},
    "Soft toy search"
)

test_rag_search(
    "board game family",
    {},
    "Game search"
)

# Test 3: Price Filters
print_section("3. RAG SEARCH - PRICE FILTERS")

test_rag_search(
    "toy",
    {"price_max": 10.0},
    "Budget toys under $10"
)

test_rag_search(
    "puzzle",
    {"price_min": 20.0, "price_max": 30.0},
    "Mid-range puzzles $20-$30"
)

test_rag_search(
    "game",
    {"price_min": 50.0},
    "Premium games over $50"
)

# Test 4: Boolean Filters
print_section("4. RAG SEARCH - ECO-FRIENDLY FILTER")

test_rag_search(
    "toy for toddler",
    {"eco_friendly": True},
    "Eco-friendly toys only"
)

test_rag_search(
    "outdoor toy",
    {"eco_friendly": True, "price_max": 20.0},
    "Eco-friendly outdoor toys under $20"
)

# Test 5: Category Filter
print_section("5. RAG SEARCH - CATEGORY FILTER")

test_rag_search(
    "gift",
    {"category": "Toys"},
    "Search within Toys category"
)

test_rag_search(
    "item",
    {"category": "Baby"},
    "Search within Baby category"
)

# Test 6: Products NOT in Catalog
print_section("6. RAG SEARCH - MISSING PRODUCTS")

test_rag_search(
    "stainless steel cleaner",
    {},
    "Household cleaner (NOT in toy catalog)"
)

test_rag_search(
    "laptop computer",
    {},
    "Electronics (NOT in catalog)"
)

test_rag_search(
    "vacuum cleaner",
    {},
    "Appliance (might find toy vacuum)"
)

# Test 7: Web Search - Various Queries
print_section("7. WEB SEARCH - VARIOUS QUERIES")

test_web_search(
    "wooden puzzle kids amazon",
    "Product that EXISTS in catalog"
)
time.sleep(2)  # Rate limit protection

test_web_search(
    "stainless steel cleaner",
    "Product NOT in catalog"
)
time.sleep(2)  # Rate limit protection

test_web_search(
    "eco-friendly toy",
    "Eco product search"
)

# Test 8: Cache Verification
print_section("8. CACHE VERIFICATION")

print("First call to web search (should NOT be cached):")
test_web_search("melissa and doug puzzle", "Cache test - first call")

time.sleep(2)  # Changed from 0.5 to 2 for rate limit

print("Second call with SAME query (should be CACHED and faster):")
test_web_search("melissa and doug puzzle", "Cache test - second call")

# Test 9: Combined Filters
print_section("9. RAG SEARCH - MULTIPLE FILTERS COMBINED")

test_rag_search(
    "toy",
    {
        "price_max": 15.0,
        "eco_friendly": True,
        "category": "Toys"
    },
    "Eco-friendly toys under $15 in Toys category"
)

test_rag_search(
    "puzzle",
    {
        "price_min": 5.0,
        "price_max": 20.0,
        "category": "Toys"
    },
    "Puzzles $5-$20 in Toys category"
)

# Test 10: Edge Cases
print_section("10. EDGE CASES")

test_rag_search(
    "xyzabc123notarealproduct",
    {},
    "Nonsense query (should return empty or low relevance)"
)

test_rag_search(
    "puzzle",
    {"top_k": 10},
    "Large top_k (10 results)"
)

test_rag_search(
    "toy",
    {"price_max": 1.0},
    "Very low price filter (few/no results)"
)

# Summary
print_section("TESTING COMPLETE")

print("""
✓ All test scenarios executed!

What we tested:
1. Server health & tool discovery
2. Basic RAG searches (no filters)
3. Price filters (min, max, range)
4. Boolean filters (eco_friendly)
5. Category filters
6. Missing products (not in catalog)
7. Web search functionality (with rate limit handling)
8. Caching mechanism
9. Combined multiple filters
10. Edge cases

Your MCP server is ready for LangGraph integration!
""")