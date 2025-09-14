from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
from indexer import MOSDACIndexer
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('api.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="MOSDAC API",
    description="API for accessing MOSDAC website content",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize indexer
indexer = MOSDACIndexer()

# Pydantic models for request/response
class SearchResponse(BaseModel):
    url: str
    title: str
    text_content: str
    meta_description: Optional[str]
    category: str
    crawl_timestamp: datetime
    announcements: Optional[List[dict]]
    services: Optional[List[dict]]
    satellite_data: Optional[List[dict]]

@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "Welcome to MOSDAC API"}

@app.get("/search", response_model=List[SearchResponse])
async def search(
    query: str = Query(..., description="Search query"),
    category: Optional[str] = Query(None, description="Filter by category"),
    size: int = Query(10, description="Number of results to return")
):
    """Search for content"""
    try:
        results = indexer.search(query, category, size)
        return results
    except Exception as e:
        logger.error(f"Error in search: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/categories")
async def get_categories():
    """Get list of available categories"""
    return {
        "categories": [
            "missions",
            "catalog",
            "galleries",
            "data_access",
            "reports",
            "services",
            "other"
        ]
    }

@app.get("/announcements")
async def get_announcements():
    """Get latest announcements"""
    try:
        results = indexer.search("", category=None, size=1)
        if results and results[0].get('announcements'):
            return {"announcements": results[0]['announcements']}
        return {"announcements": []}
    except Exception as e:
        logger.error(f"Error getting announcements: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/services")
async def get_services():
    """Get all services"""
    try:
        results = indexer.search("", category="services", size=1)
        if results and results[0].get('services'):
            return {"services": results[0]['services']}
        return {"services": []}
    except Exception as e:
        logger.error(f"Error getting services: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/satellite-data")
async def get_satellite_data():
    """Get all satellite data"""
    try:
        results = indexer.search("", category="data_access", size=1)
        if results and results[0].get('satellite_data'):
            return {"satellite_data": results[0]['satellite_data']}
        return {"satellite_data": []}
    except Exception as e:
        logger.error(f"Error getting satellite data: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 