from fastapi import HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from sqlalchemy.orm import Session

from app.core.mongodb import is_valid_object_id, str_to_object_id
from app.models.itinerary import Itinerary, ItineraryItem
from app.models.trip import Trip


def get_or_create_itinerary(trip: Trip, db: Session) -> Itinerary:
    """Retrieve existing itinerary for trip or create a new persistent one."""
    itinerary = db.query(Itinerary).filter(Itinerary.trip_id == trip.id).first()
    if not itinerary:
        itinerary = Itinerary(trip_id=trip.id, estimated_total_cost=0.0)
        db.add(itinerary)
        db.commit()
        db.refresh(itinerary)
    return itinerary


async def validate_hotel_id(hotel_id: str, mongo_db: AsyncIOMotorDatabase) -> dict:
    """Validate that hotel_id is a valid ObjectId and exists in the MongoDB catalogue."""
    if not is_valid_object_id(hotel_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid hotel ID format: '{hotel_id}'"
        )
    hotel = await mongo_db["hotels"].find_one({"_id": str_to_object_id(hotel_id)})
    if not hotel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Hotel with ID '{hotel_id}' not found in catalogue"
        )
    return hotel


async def validate_flight_id(
    flight_id: str,
    mongo_db: AsyncIOMotorDatabase,
    label: str = "Flight"
) -> dict:
    """Validate that flight_id is a valid ObjectId and exists in the MongoDB catalogue."""
    if not is_valid_object_id(flight_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid {label.lower()} ID format: '{flight_id}'"
        )
    flight = await mongo_db["flights"].find_one({"_id": str_to_object_id(flight_id)})
    if not flight:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{label} with ID '{flight_id}' not found in catalogue"
        )
    return flight


async def validate_activity_id(activity_id: str, mongo_db: AsyncIOMotorDatabase) -> dict:
    """Validate that activity_id is a valid ObjectId and exists in the MongoDB catalogue."""
    if not is_valid_object_id(activity_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid activity ID format: '{activity_id}'"
        )
    activity = await mongo_db["activities"].find_one({"_id": str_to_object_id(activity_id)})
    if not activity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Activity with ID '{activity_id}' not found in catalogue"
        )
    return activity


async def recalculate_itinerary_cost(
    itinerary: Itinerary,
    trip: Trip,
    mongo_db: AsyncIOMotorDatabase,
    db: Session = None,
) -> float:
    """
    Calculate and persist estimated total cost based on selected hotel,
    outbound/return flights, and scheduled activities.
    """
    nights = max(1, (trip.end_date - trip.start_date).days)
    travellers = max(1, trip.travellers or 1)

    # 1. Hotel Cost = price_per_night * nights
    hotel_cost = 0.0
    if itinerary.selected_hotel_id and is_valid_object_id(itinerary.selected_hotel_id):
        hotel = await mongo_db["hotels"].find_one({"_id": str_to_object_id(itinerary.selected_hotel_id)})
        if hotel:
            hotel_cost = float(hotel.get("price_per_night", 0.0)) * nights

    # 2. Flight Cost = (outbound + return) * travellers
    outbound_cost = 0.0
    if itinerary.outbound_flight_id and is_valid_object_id(itinerary.outbound_flight_id):
        outbound = await mongo_db["flights"].find_one({"_id": str_to_object_id(itinerary.outbound_flight_id)})
        if outbound:
            outbound_cost = float(outbound.get("price", 0.0)) * travellers

    return_cost = 0.0
    if itinerary.return_flight_id and is_valid_object_id(itinerary.return_flight_id):
        return_flight = await mongo_db["flights"].find_one({"_id": str_to_object_id(itinerary.return_flight_id)})
        if return_flight:
            return_cost = float(return_flight.get("price", 0.0)) * travellers

    flights_cost = outbound_cost + return_cost

    # 3. Activities Cost = sum of item estimated_cost
    if db is not None:
        active_items = db.query(ItineraryItem).filter(ItineraryItem.itinerary_id == itinerary.id).all()
    else:
        active_items = list(itinerary.items)

    activities_cost = sum(float(item.estimated_cost or 0.0) for item in active_items)

    total_cost = round(hotel_cost + flights_cost + activities_cost, 2)
    itinerary.estimated_total_cost = total_cost
    return total_cost
