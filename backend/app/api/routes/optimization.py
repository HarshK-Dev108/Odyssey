from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase
from sqlalchemy.orm import Session

from app.schemas.optimization import OptimizationRequest
from app.core.database import get_db
from app.core.auth import get_current_user
from app.core.mongodb import get_database
from app.models.trip import Trip
from app.models.user import User
from app.services.tourism_service import get_tourism_options

from app.ai.recommendation.recommender import TravelRecommender
from app.ai.optimizer.budget_optimizer import BudgetOptimizer


router = APIRouter(
    prefix="/api/v1/trips",
    tags=["Optimization"]
)


recommender = TravelRecommender()
budget_optimizer = BudgetOptimizer()


@router.post("/{trip_id}/optimize")
async def optimize_trip(
    trip_id: int,
    request: OptimizationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tourism_db: AsyncIOMotorDatabase = Depends(get_database),
):
    trip = db.query(Trip).filter(
        Trip.id == trip_id,
        Trip.user_id == current_user.id,
    ).first()

    if not trip:
        raise HTTPException(
            status_code=404,
            detail="Trip not found"
        )

    days = max((trip.end_date - trip.start_date).days, 1)
    options = await get_tourism_options(
        db=tourism_db,
        destination=trip.destination,
        from_city=trip.from_city,
        nights=days,
        travellers=trip.travellers,
    )

    if trip.ai_plan and trip.ai_plan.get("budget_plan"):
        current_plan = trip.ai_plan
    else:
        recommendations = recommender.recommend(
            options=options,
            interests=trip.interests or [],
            budget=trip.budget,
            hotel_rating=trip.hotel_rating,
        )
        current_plan = budget_optimizer.optimize(
            recommendations=recommendations,
            budget=trip.budget,
            interests=trip.interests or [],
            hotel_rating=trip.hotel_rating,
            pace=trip.pace,
            avoid_crowds=trip.avoid_crowds,
            days=days,
        )
        current_plan = {
            "budget_plan": current_plan,
            "itinerary": [],
        }
        trip.ai_plan = current_plan

    user_request = request.request.lower()

    # --------------------------------
    # Make trip cheaper
    # --------------------------------
    if "cheaper" in user_request or "cheap" in user_request:

        saving = 10000

        optimized_plan = budget_optimizer.make_cheaper(
            selected_options=current_plan["budget_plan"]["selected_options"],
            target_saving=saving,
            available_options=options,
            budget=trip.budget,
        )

        if optimized_plan["saving"] > 0:
            trip.ai_plan["budget_plan"]["selected_options"] = optimized_plan["selected_options"]
            trip.ai_plan["budget_plan"]["total_cost"] = optimized_plan["new_cost"]
            trip.ai_plan["budget_plan"]["remaining_budget"] = trip.budget - optimized_plan["new_cost"]
            trip.ai_plan["budget_plan"]["budget_utilization"] = round(
                (optimized_plan["new_cost"] / trip.budget) * 100, 2
            ) if trip.budget else 0
            db.commit()

        return {
            "trip_id": trip.id,
            "request": request.request,
            "optimization": "make_cheaper",
            "target_saving": saving,
            "result": optimized_plan
        }

    # --------------------------------
    # Upgrade hotel
    # --------------------------------
    if (
        "better hotel" in user_request
        or "upgrade hotel" in user_request
        or "better hotel" in user_request
        or "hotel upgrade" in user_request
    ):

        optimized_plan = budget_optimizer.upgrade_hotel(
            selected_options=current_plan["budget_plan"]["selected_options"],
            available_hotels=options,
            budget=trip.budget
        )

        if optimized_plan.get("success"):
            trip.ai_plan["budget_plan"]["selected_options"] = optimized_plan["selected_options"]
            trip.ai_plan["budget_plan"]["total_cost"] = optimized_plan["new_cost"]
            trip.ai_plan["budget_plan"]["remaining_budget"] = optimized_plan["remaining_budget"]
            trip.ai_plan["budget_plan"]["budget_utilization"] = round(
                (optimized_plan["new_cost"] / trip.budget) * 100, 2
            ) if trip.budget else 0
            db.commit()

        return {
            "trip_id": trip.id,
            "request": request.request,
            "optimization": "upgrade_hotel",
            "result": optimized_plan
        }

    # --------------------------------
    # Default response
    # --------------------------------
    return {
        "trip_id": trip.id,
        "request": request.request,
        "current_plan": current_plan,
        "message": "Optimization request received"
    }