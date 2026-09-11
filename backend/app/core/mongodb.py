import os
import logging
from typing import Optional
from bson import ObjectId
from bson.errors import InvalidId
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME", "odyssey_tourism")


class MongoDBManager:
    client: Optional[AsyncIOMotorClient] = None
    db: Optional[AsyncIOMotorDatabase] = None


db_manager = MongoDBManager()


async def connect_to_mongo() -> None:
    """Initialize the MongoDB client connection."""
    try:
        db_manager.client = AsyncIOMotorClient(
            MONGODB_URL,
            serverSelectionTimeoutMS=2000
        )
        db_manager.db = db_manager.client[MONGODB_DB_NAME]
        logger.info(f"Connected to MongoDB at {MONGODB_URL}, database: {MONGODB_DB_NAME}")
    except Exception as e:
        logger.warning(f"Could not connect to MongoDB on startup: {e}")


async def close_mongo_connection() -> None:
    """Close the MongoDB client connection."""
    if db_manager.client:
        db_manager.client.close()
        db_manager.client = None
        db_manager.db = None
        logger.info("MongoDB connection closed.")


def get_database() -> AsyncIOMotorDatabase:
    """
    Get the configured MongoDB database instance.
    If not connected yet, lazily initializes the client.
    """
    if db_manager.db is None:
        db_manager.client = AsyncIOMotorClient(
            MONGODB_URL,
            serverSelectionTimeoutMS=2000
        )
        db_manager.db = db_manager.client[MONGODB_DB_NAME]
    return db_manager.db


def is_valid_object_id(val: str) -> bool:
    """Check whether a string is a valid 24-character hex ObjectId."""
    return ObjectId.is_valid(val)


def str_to_object_id(val: str) -> ObjectId:
    """Convert string to BSON ObjectId, raising ValueError if invalid."""
    try:
        return ObjectId(val)
    except (InvalidId, TypeError) as e:
        raise ValueError(f"Invalid ObjectId: {val}") from e


def serialize_doc(doc: Optional[dict]) -> Optional[dict]:
    """Helper to convert MongoDB _id to string 'id' for Pydantic serialization."""
    if doc is None:
        return None
    d = dict(doc)
    if "_id" in d:
        d["id"] = str(d.pop("_id"))
    return d
