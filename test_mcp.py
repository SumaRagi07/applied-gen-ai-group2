import requests
import json

BASE_URL = "http://localhost:8000"

print("Testing MCP Server...\n")

# Test 1: Health check
print("1. Health Check:")
response = requests.get(f"{BASE_URL}/health")
print(f"   Status: {response.status_code}")
print(f"   Response: {response.json()}\n")

# Test 2: List tools
print("2. List Tools:")
response = requests.get(f"{BASE_URL}/tools")
print(f"   Status: {response.status_code}")
tools = response.json()
print(f"   Available tools: {[t['name'] for t in tools['tools']]}\n")

# Test 3: RAG Search - wooden puzzle
print("3. RAG Search - wooden puzzle under $20:")
response = requests.post(
    f"{BASE_URL}/call",
    json={
        "tool": "rag.search",
        "params": {
            "query": "wooden puzzle for kids",
            "price_max": 20,
            "top_k": 3
        }
    }
)
print(f"   Status: {response.status_code}")
result = response.json()
if result['success']:
    print(f"   Found: {result['data']['total_found']} products")
    print(f"   Query time: {result['execution_time_ms']}ms")
    for i, product in enumerate(result['data']['results'][:3], 1):
        print(f"   {i}. {product['title'][:60]}... - ${product['price']}")
else:
    print(f"   Error: {result['error']}")
print()

# Test 4: Web Search
print("4. Web Search - wooden puzzle:")
response = requests.post(
    f"{BASE_URL}/call",
    json={
        "tool": "web.search",
        "params": {
            "query": "wooden puzzle for kids",
            "max_results": 3
        }
    }
)
print(f"   Status: {response.status_code}")
result = response.json()
if result['success']:
    print(f"   Found: {result['data']['total_found']} results")
    print(f"   Cached: {result['data']['cached']}")
    print(f"   Query time: {result['execution_time_ms']}ms")
    for i, item in enumerate(result['data']['results'][:3], 1):
        print(f"   {i}. {item['title'][:60]}...")
        print(f"      Price: {item['price']} | Source: {item['source']}")
else:
    print(f"   Error: {result['error']}")
print()

print("✓ All tests complete!")