from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase
from sqlalchemy.orm import Session

from app.schemas.chat import ChatRequest
from app.core.database import get_db
from app.core.auth import get_current_user
from app.core.mongodb import get_database
from app.models.trip import Trip
from app.models.user import User
from app.services.assistant_service import AssistantService


router = APIRouter(
    prefix="/api/v1/trips",
    tags=["AI Assistant"]
)


assistant_service = AssistantService()


@router.post("/{trip_id}/chat")
async def travel_chat(
    trip_id: int,
    request: ChatRequest,
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

    response = await assistant_service.respond(
        trip=trip,
        message=request.message,
        tourism_db=tourism_db,
    )
    db.commit()
    return response