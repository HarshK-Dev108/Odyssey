import logging
from pymongo import ASCENDING, DESCENDING
from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)


async def create_indexes(db: AsyncIOMotorDatabase) -> None:
    """
    Create sensible MongoDB indexes for frequently queried tourism fields.
    Safely catches and logs errors if database is temporarily unavailable.
    """
    try:
        # Destinations
        await db["destinations"].create_index([("country", ASCENDING)], name="idx_destinations_country")
        await db["destinations"].create_index([("name", ASCENDING)], name="idx_destinations_name")

        # Hotels
        await db["hotels"].create_index([("destination_id", ASCENDING)], name="idx_hotels_dest_id")
        await db["hotels"].create_index([("rating", DESCENDING)], name="idx_hotels_rating")
        await db["hotels"].create_index([("price_per_night", ASCENDING)], name="idx_hotels_price")

        # Flights
        await db["flights"].create_index([("origin", ASCENDING)], name="idx_flights_origin")
        await db["flights"].create_index([("destination", ASCENDING)], name="idx_flights_destination")
        await db["flights"].create_index([("price", ASCENDING)], name="idx_flights_price")

        # Activities
        await db["activities"].create_index([("destination_id", ASCENDING)], name="idx_activities_dest_id")
        await db["activities"].create_index([("category", ASCENDING)], name="idx_activities_category")
        await db["activities"].create_index([("rating", DESCENDING)], name="idx_activities_rating")

        # Expenses
        await db["expenses"].create_index([("trip_id", ASCENDING)], name="idx_expenses_trip_id")
        await db["expenses"].create_index([("category", ASCENDING)], name="idx_expenses_category")

        logger.info("Tourism collection MongoDB indexes ensured successfully.")
    except Exception as e:
        logger.warning(f"Could not create MongoDB indexes on startup: {e}")
