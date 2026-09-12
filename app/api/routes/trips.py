from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase
from sqlalchemy.orm import Session

from app.schemas.trip import TripRequest, TripUpdateRequest
from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.trip import Trip
from app.models.user import User

from app.core.mongodb import get_database
from app.services.tourism_service import get_tourism_options

from app.ai.recommendation.recommender import TravelRecommender
from app.ai.optimizer.budget_optimizer import BudgetOptimizer
from app.ai.itinerary.itinerary_generator import ItineraryGenerator
from app.ai.agent.travel_agent import TravelAgent


router = APIRouter(
    prefix="/api/v1/trips",
    tags=["Trips"]
)


# Create AI components
recommender = TravelRecommender()
budget_optimizer = BudgetOptimizer()
itinerary_generator = ItineraryGenerator()

travel_agent = TravelAgent(
    recommender=recommender,
    budget_optimizer=budget_optimizer,
    itinerary_generator=itinerary_generator
)


def serialize_trip(trip: Trip) -> dict:
    return {
        "trip_id": trip.id,
        "id": trip.id,
        "user_id": trip.user_id,
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
        "avoid_crowds": trip.avoid_crowds,
        "ai_plan": trip.ai_plan
    }


def _get_user_trip(trip_id: int, db: Session, user: User) -> Trip:
    trip = db.query(Trip).filter(
        Trip.id == trip_id,
        Trip.user_id == user.id,
    ).first()

    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    return trip


@router.post("/plan")
async def create_trip_plan(
    trip: TripRequest,
    db: Session = Depends(get_db),
    tourism_db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: User = Depends(get_current_user),
):

    # Save trip in database
    new_trip = Trip(
        user_id=current_user.id,
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

    # Calculate number of days
    days = (trip.end_date - trip.start_date).days

    if days < 1:
        days = 1

    options = await get_tourism_options(
        db=tourism_db,
        destination=trip.destination,
        from_city=trip.from_city,
        nights=days,
        travellers=trip.travellers,
    )

    # Run AI travel pipeline
    ai_plan = travel_agent.plan_trip(
        options=options,
        interests=trip.interests,
        budget=trip.budget,
        hotel_rating=trip.hotel_rating,
        days=days,
        pace=trip.pace,
        avoid_crowds=trip.avoid_crowds,
    )

    # Save AI-generated travel plan in database
    new_trip.ai_plan = ai_plan

    db.commit()
    db.refresh(new_trip)

    return {
        "message": "AI travel plan created successfully",
        "trip_id": new_trip.id,
        "trip": trip.model_dump(),
        "ai_plan": ai_plan
    }


@router.get("/")
def list_trips(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    trips = (
        db.query(Trip)
        .filter(Trip.user_id == current_user.id)
        .order_by(Trip.id.desc())
        .all()
    )
    return [serialize_trip(trip) for trip in trips]


@router.get("/{trip_id}")
def get_trip(
    trip_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    trip = _get_user_trip(trip_id, db, current_user)
    return serialize_trip(trip)


@router.put("/{trip_id}")
@router.patch("/{trip_id}")
def update_trip(
    trip_id: int,
    payload: TripUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    trip = _get_user_trip(trip_id, db, current_user)

    update_data = payload.model_dump(exclude_unset=True)

    # Validate date consistency if dates are updated
    start_date = update_data.get("start_date", trip.start_date)
    end_date = update_data.get("end_date", trip.end_date)
    if end_date <= start_date:
        raise HTTPException(
            status_code=400,
            detail="end_date must be after start_date"
        )

    for field, value in update_data.items():
        setattr(trip, field, value)

    db.commit()
    db.refresh(trip)

    res = serialize_trip(trip)
    res["message"] = "Trip updated successfully"
    return res


@router.delete("/{trip_id}")
def delete_trip(
    trip_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    trip = _get_user_trip(trip_id, db, current_user)

    db.delete(trip)
    db.commit()

    return {
        "message": "Trip deleted successfully",
        "trip_id": trip_id
    }