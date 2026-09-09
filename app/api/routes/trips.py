from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase
from sqlalchemy.orm import Session

from app.schemas.trip import TripRequest
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


@router.get("/{trip_id}")
def get_trip(
    trip_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    trip = db.query(Trip).filter(
        Trip.id == trip_id,
        Trip.user_id == current_user.id,
    ).first()

    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

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
        "avoid_crowds": trip.avoid_crowds,
        "ai_plan": trip.ai_plan
    }