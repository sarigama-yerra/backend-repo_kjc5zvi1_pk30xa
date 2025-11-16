"""
Database Helper Functions

MongoDB helper functions ready to use in your backend code.
Import and use these functions in your API endpoints for database operations.
"""

from pymongo import MongoClient
from datetime import datetime, timezone
import os
from dotenv import load_dotenv
from typing import Union, Optional, Dict, Any
from pydantic import BaseModel
from bson import ObjectId

# Load environment variables from .env file
load_dotenv()

_client = None
db = None

database_url = os.getenv("DATABASE_URL")
database_name = os.getenv("DATABASE_NAME")

if database_url and database_name:
    _client = MongoClient(database_url)
    db = _client[database_name]

# Helper functions for common database operations
def create_document(collection_name: str, data: Union[BaseModel, dict]):
    """Insert a single document with timestamp"""
    if db is None:
        raise Exception("Database not available. Check DATABASE_URL and DATABASE_NAME environment variables.")

    # Convert Pydantic model to dict if needed
    if isinstance(data, BaseModel):
        data_dict = data.model_dump()
    else:
        data_dict = data.copy()

    data_dict['created_at'] = datetime.now(timezone.utc)
    data_dict['updated_at'] = datetime.now(timezone.utc)

    result = db[collection_name].insert_one(data_dict)
    return str(result.inserted_id)

def get_documents(collection_name: str, filter_dict: dict = None, limit: int = None):
    """Get documents from collection"""
    if db is None:
        raise Exception("Database not available. Check DATABASE_URL and DATABASE_NAME environment variables.")
    
    cursor = db[collection_name].find(filter_dict or {})
    if limit:
        cursor = cursor.limit(limit)
    
    return list(cursor)


def update_document_by_id(collection_name: str, doc_id: Union[str, ObjectId], update: Dict[str, Any]):
    """Update a single document by its _id with $set and updated_at timestamp"""
    if db is None:
        raise Exception("Database not available. Check DATABASE_URL and DATABASE_NAME environment variables.")

    if isinstance(doc_id, str):
        try:
            doc_id = ObjectId(doc_id)
        except Exception:
            raise ValueError("Invalid ObjectId string")

    update_data = update.copy()
    update_data['updated_at'] = datetime.now(timezone.utc)
    res = db[collection_name].update_one({"_id": doc_id}, {"$set": update_data})
    return res.modified_count


def update_documents(collection_name: str, filter_dict: Dict[str, Any], update: Dict[str, Any]):
    """Update multiple documents matching a filter"""
    if db is None:
        raise Exception("Database not available. Check DATABASE_URL and DATABASE_NAME environment variables.")

    update_data = update.copy()
    update_data['updated_at'] = datetime.now(timezone.utc)
    res = db[collection_name].update_many(filter_dict, {"$set": update_data})
    return res.modified_count
