from indexer import MOSDACIndexer

def test_search():
    # Initialize the indexer
    indexer = MOSDACIndexer()
    
    # Index the test data
    print("Indexing test data...")
    indexer.index_from_file('scraped_data.json')
    
    # Test search
    print("\nTesting search functionality...")
    results = indexer.search("test")
    print(f"\nFound {len(results)} results:")
    for result in results:
        print(f"\nTitle: {result['title']}")
        print(f"URL: {result['url']}")
        print(f"Content: {result['text_content'][:100]}...")

if __name__ == "__main__":
    test_search()