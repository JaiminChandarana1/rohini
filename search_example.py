from indexer import MOSDACIndexer

def perform_search():
    # Initialize the indexer
    indexer = MOSDACIndexer()
    
    # Example 1: Basic search
    print("\n1. Basic search for 'satellite':")
    results = indexer.search("satellite")
    for doc in results:
        print(f"\nTitle: {doc['title']}")
        print(f"URL: {doc['url']}")
        print(f"Description: {doc['meta_description']}")
    
    # Example 2: Search with category filter
    print("\n2. Search for 'data' in satellite category:")
    results = indexer.search("data", category="satellite")
    for doc in results:
        print(f"\nTitle: {doc['title']}")
        print(f"URL: {doc['url']}")
        print(f"Description: {doc['meta_description']}")
    
    # Example 3: Search with multiple words
    print("\n3. Search for 'weather forecast':")
    results = indexer.search("weather forecast")
    for doc in results:
        print(f"\nTitle: {doc['title']}")
        print(f"URL: {doc['url']}")
        print(f"Description: {doc['meta_description']}")

if __name__ == "__main__":
    perform_search() 