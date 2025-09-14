from indexer import MOSDACIndexer

def test_connection():
    try:
        print("Testing PostgreSQL connection...")
        indexer = MOSDACIndexer()
        print("Successfully connected to PostgreSQL!")
    except Exception as e:
        print(f"Error connecting to PostgreSQL: {str(e)}")

if __name__ == "__main__":
    test_connection() 