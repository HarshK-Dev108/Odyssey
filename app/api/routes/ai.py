from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.auth import get_current_user
from app.core.mongodb import get_database
from app.models.trip import Trip
from app.models.user import User
from app.schemas.ai_chat import AIChatRequest, AIChatResponse
from app.services.itinerary_service import get_or_create_itinerary
from app.services.replanning_service import execute_ai_replanning
from app.ai.llm.provider import LLMProvider

router = APIRouter(
    prefix="/api/v1/ai",
    tags=["YatraAI Travel Assistant"]
)

llm_provider = LLMProvider()


@router.post("/chat", response_model=AIChatResponse)
async def ai_trip_chat(
    request: AIChatRequest,
    db: Session = Depends(get_db),
    mongo_db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: User = Depends(get_current_user),
):
    """
    YatraAI conversational assistant endpoint for dynamic itinerary replanning.
    Interprets user intent via LLM, validates structured action, and applies
    deterministic updates to the user's persisted itinerary.
    """
    trip = db.query(Trip).filter(
        Trip.id == request.trip_id,
        Trip.user_id == current_user.id,
    ).first()

    if not trip:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trip not found"
        )

    itinerary = get_or_create_itinerary(trip, db)
    return await execute_ai_replanning(
        trip=trip,
        itinerary=itinerary,
        user_message=request.message,
        llm_provider=llm_provider,
        mongo_db=mongo_db,
        db=db,
    )
