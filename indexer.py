import json
import logging
from typing import Dict, List
import os
from dotenv import load_dotenv
from datetime import datetime
import psycopg2
from psycopg2.extras import Json
import re

class MOSDACIndexer:
    def __init__(self):
        self.setup_logging()
        self.setup_postgresql()
        self.table_name = "mosdac_content"

    def setup_logging(self):
        """Configure logging for the indexer"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('indexer.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    def setup_postgresql(self):
        """Setup PostgreSQL connection"""
        # Load environment variables from .env file
        load_dotenv(override=True)
        
        # Get PostgreSQL configuration from environment variables
        db_host = os.getenv('DB_HOST', 'localhost')
        db_port = os.getenv('DB_PORT', '5432')
        db_name = os.getenv('DB_NAME', 'rohini')
        db_user = os.getenv('DB_USER', 'postgres')
        db_password = os.getenv('DB_PASSWORD', 'JDCpostgres.@')

        # Log connection details (without password)
        self.logger.info(f"Connecting to PostgreSQL at {db_host}:{db_port}, database: {db_name}, user: {db_user}")

        try:
            # Initialize PostgreSQL connection
            self.conn = psycopg2.connect(
                host=db_host,
                port=db_port,
                dbname=db_name,
                user=db_user,
                password=db_password
            )
            self.conn.autocommit = True
            self.cursor = self.conn.cursor()
            self.logger.info("Successfully connected to PostgreSQL")
        except Exception as e:
            self.logger.error(f"Failed to connect to PostgreSQL: {str(e)}")
            raise

    def create_index(self):
        """Create PostgreSQL table with enhanced full-text search capabilities"""
        try:
            # Create the main table with improved search vector
            self.cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS {self.table_name} (
                    url TEXT PRIMARY KEY,
                    title TEXT,
                    text_content TEXT,
                    meta_description TEXT,
                    tables JSONB,
                    links TEXT[],
                    aria_labels JSONB,
                    crawl_timestamp TIMESTAMP,
                    category TEXT,
                    announcements JSONB,
                    services JSONB,
                    satellite_data JSONB,
                    search_vector tsvector GENERATED ALWAYS AS (
                        setweight(to_tsvector('english', coalesce(title, '')), 'A') ||
                        setweight(to_tsvector('english', coalesce(text_content, '')), 'B') ||
                        setweight(to_tsvector('english', coalesce(meta_description, '')), 'C') ||
                        setweight(to_tsvector('english', coalesce(category, '')), 'D')
                    ) STORED
                )
            """)

            # Create GIN index for full-text search
            self.cursor.execute(f"""
                CREATE INDEX IF NOT EXISTS {self.table_name}_search_idx 
                ON {self.table_name} USING GIN (search_vector)
            """)

            # Create index on category for faster filtering
            self.cursor.execute(f"""
                CREATE INDEX IF NOT EXISTS {self.table_name}_category_idx 
                ON {self.table_name} (category)
            """)

            self.logger.info(f"Created table and indexes: {self.table_name}")
        except Exception as e:
            self.logger.error(f"Error creating table: {str(e)}")
            raise

    def index_document(self, document: Dict):
        """Index a single document with improved data handling"""
        try:
            # Convert crawl_timestamp to datetime if it's a string
            if isinstance(document.get('crawl_timestamp'), str):
                document['crawl_timestamp'] = datetime.fromisoformat(document['crawl_timestamp'])

            # Clean and normalize text fields
            for field in ['title', 'text_content', 'meta_description']:
                if field in document and document[field]:
                    document[field] = self.clean_text(document[field])

            # Convert dictionary fields to JSON
            json_fields = ['tables', 'aria_labels', 'announcements', 'services', 'satellite_data']
            for field in json_fields:
                if field in document and document[field] is not None:
                    document[field] = Json(document[field])

            # Convert links to array if it's not already
            if 'links' in document and document['links'] is not None:
                if not isinstance(document['links'], list):
                    document['links'] = [document['links']]
                # Clean and normalize links
                document['links'] = [self.clean_url(link) for link in document['links'] if link]

            # Prepare the SQL query
            columns = ', '.join(document.keys())
            values = ', '.join(['%s'] * len(document))
            query = f"""
                INSERT INTO {self.table_name} ({columns})
                VALUES ({values})
                ON CONFLICT (url) DO UPDATE SET
                {', '.join(f"{k} = EXCLUDED.{k}" for k in document.keys())}
            """

            # Execute the query
            self.cursor.execute(query, list(document.values()))
            self.logger.info(f"Indexed document: {document['url']}")
        except Exception as e:
            self.logger.error(f"Error indexing document {document['url']}: {str(e)}")
            raise

    def clean_text(self, text: str) -> str:
        """Clean and normalize text content"""
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove special characters but keep important ones
        text = re.sub(r'[^\w\s.,!?-]', '', text)
        return text.strip()

    def clean_url(self, url: str) -> str:
        """Clean and normalize URLs"""
        # Remove trailing slashes and normalize
        url = url.rstrip('/')
        # Remove query parameters if they're not essential
        if '?' in url and not any(param in url for param in ['id=', 'page=', 'view=']):
            url = url.split('?')[0]
        return url

    def bulk_index(self, documents: List[Dict]):
        """Bulk index multiple documents"""
        try:
            for doc in documents:
                self.index_document(doc)
            self.logger.info(f"Bulk indexed {len(documents)} documents")
        except Exception as e:
            self.logger.error(f"Error in bulk indexing: {str(e)}")
            raise

    def index_from_file(self, file_path: str):
        """Index documents from a JSON file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                documents = json.load(f)
            
            self.create_index()
            self.bulk_index(documents)
            self.logger.info(f"Successfully indexed documents from {file_path}")
        except Exception as e:
            self.logger.error(f"Error indexing from file {file_path}: {str(e)}")
            raise

    def search(self, query: str, category: str = None, size: int = 10) -> List[Dict]:
        """Enhanced search with better query processing and ranking"""
        try:
            # Clean and prepare the query
            query = self.clean_text(query)
            
            # Create a more sophisticated search query
            search_query = f"""
                SELECT 
                    *,
                    ts_rank_cd(search_vector, plainto_tsquery('english', %s)) as rank
                FROM {self.table_name}
                WHERE search_vector @@ plainto_tsquery('english', %s)
            """
            params = [query, query]

            # Add category filter if specified
            if category:
                search_query += " AND category = %s"
                params.append(category)

            # Add ordering by rank and limit
            search_query += " ORDER BY rank DESC LIMIT %s"
            params.append(size)

            # Execute the query
            self.cursor.execute(search_query, params)
            columns = [desc[0] for desc in self.cursor.description]
            results = []
            
            for row in self.cursor.fetchall():
                doc = dict(zip(columns, row))
                # Convert JSONB fields back to Python objects
                for field in ['tables', 'aria_labels', 'announcements', 'services', 'satellite_data']:
                    if field in doc and doc[field]:
                        doc[field] = doc[field]
                results.append(doc)

            return results
        except Exception as e:
            self.logger.error(f"Error searching: {str(e)}")
            return []

    def __del__(self):
        """Cleanup database connection"""
        if hasattr(self, 'cursor'):
            self.cursor.close()
        if hasattr(self, 'conn'):
            self.conn.close()

if __name__ == "__main__":
    indexer = MOSDACIndexer()
    indexer.index_from_file('scraped_data.json') 