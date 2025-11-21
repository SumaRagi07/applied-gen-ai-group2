import sys
sys.path.append('.')

from src.agents.graph import agent_graph

def test_query(query):
    """Test a single query through the agent graph"""
    
    print("\n" + "="*70)
    print(f"QUERY: {query}")
    print("="*70)
    
    # Run through graph
    result = agent_graph.invoke({
        "user_query": query
    })
    
    # Print results
    print("\n" + "="*70)
    print("FINAL ANSWER:")
    print("="*70)
    print(result['final_answer'])
    
    print("\n" + "="*70)
    print(f"CITATIONS: {len(result.get('citations', []))}")
    print("="*70)
    for citation in result.get('citations', []):
        print(f"  - {citation}")
    
    print("\n")
    return result

if __name__ == "__main__":
    print("\n🤖 LangGraph Agent System - Testing\n")
    
    # Test 1: Product exists in catalog
    print("\n### TEST 1: Product EXISTS in catalog ###")
    test_query("Find me a wooden puzzle for kids under $20")
    
    # Test 2: Product NOT in catalog
    print("\n### TEST 2: Product NOT in catalog ###")
    test_query("I need a stainless steel cleaner")
    
    # Test 3: Eco-friendly filter
    print("\n### TEST 3: Eco-friendly filter ###")
    test_query("Show me eco-friendly toys under $15")
    
    print("\n✅ All tests complete!\n")