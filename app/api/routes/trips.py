from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.schemas.trip import TripRequest
from app.core.database import get_db
from app.models.trip import Trip


router = APIRouter(
    prefix="/api/v1/trips",
    tags=["Trips"]
)


# Create a new trip
@router.post("/plan")
def create_trip_plan(
    trip: TripRequest,
    db: Session = Depends(get_db)
):
    new_trip = Trip(
        from_city=trip.from_city,
        destination=trip.destination,
        start_date=trip.start_date,
        end_date=trip.end_date,
        travellers=trip.travellers,
        budget=trip.budget,
        currency=trip.currency,
        interests=trip.interests,
        hotel_rating=trip.hotel_rating,
        pace=trip.pace,
        avoid_crowds=trip.avoid_crowds
    )

    db.add(new_trip)
    db.commit()
    db.refresh(new_trip)

    return {
        "message": "Trip created successfully",
        "trip_id": new_trip.id,
        "trip": trip.model_dump()
    }


# Get a trip by ID
@router.get("/{trip_id}")
def get_trip(
    trip_id: int,
    db: Session = Depends(get_db)
):
    trip = db.query(Trip).filter(Trip.id == trip_id).first()

    if not trip:
        return {
            "message": "Trip not found"
        }

    return {
        "trip_id": trip.id,
        "from_city": trip.from_city,
        "destination": trip.destination,
        "start_date": trip.start_date,
        "end_date": trip.end_date,
        "travellers": trip.travellers,
        "budget": trip.budget,
        "currency": trip.currency,
        "interests": trip.interests,
        "hotel_rating": trip.hotel_rating,
        "pace": trip.pace,
        "avoid_crowds": trip.avoid_crowds
    }