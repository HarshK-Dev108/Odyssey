from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.auth import get_current_user
from app.core.mongodb import get_database
from app.models.trip import Trip
from app.models.user import User
from app.models.itinerary import Itinerary, ItineraryItem
from app.schemas.itinerary import (
    ItineraryResponse,
    HotelSelectionRequest,
    FlightsSelectionRequest,
    ActivityMutationRequest,
)
from app.schemas.generator import ItineraryGenerationResponse
from app.services.itinerary_service import (
    get_or_create_itinerary,
    validate_hotel_id,
    validate_flight_id,
    validate_activity_id,
    recalculate_itinerary_cost,
)
from app.services.itinerary_generator_service import generate_intelligent_itinerary

router = APIRouter(
    prefix="/api/v1/trips",
    tags=["Itineraries"]
)


def _get_user_trip(trip_id: int, db: Session, user: User) -> Trip:
    """Verify that the trip exists and is owned by the authenticated user."""
    trip = db.query(Trip).filter(
        Trip.id == trip_id,
        Trip.user_id == user.id,
    ).first()

    if not trip:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trip not found"
        )

    return trip


@router.get("/{trip_id}/itinerary", response_model=ItineraryResponse)
async def get_trip_itinerary(
    trip_id: int,
    db: Session = Depends(get_db),
    mongo_db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: User = Depends(get_current_user),
):
    """Retrieve the persistent itinerary for a user's trip, initializing if empty."""
    trip = _get_user_trip(trip_id, db, current_user)
    itinerary = get_or_create_itinerary(trip, db)
    await recalculate_itinerary_cost(itinerary, trip, mongo_db, db=db)
    db.commit()
    db.refresh(itinerary)
    return itinerary


@router.put("/{trip_id}/hotel", response_model=ItineraryResponse)
async def set_trip_hotel(
    trip_id: int,
    payload: HotelSelectionRequest,
    db: Session = Depends(get_db),
    mongo_db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: User = Depends(get_current_user),
):
    """Set or replace the selected hotel reference from the MongoDB catalogue."""
    trip = _get_user_trip(trip_id, db, current_user)
    itinerary = get_or_create_itinerary(trip, db)

    if payload.hotel_id is not None and str(payload.hotel_id).strip():
        hotel_str = str(payload.hotel_id).strip()
        await validate_hotel_id(hotel_str, mongo_db)
        itinerary.selected_hotel_id = hotel_str
    else:
        itinerary.selected_hotel_id = None

    await recalculate_itinerary_cost(itinerary, trip, mongo_db, db=db)
    db.commit()
    db.refresh(itinerary)
    return itinerary


@router.put("/{trip_id}/flights", response_model=ItineraryResponse)
async def set_trip_flights(
    trip_id: int,
    payload: FlightsSelectionRequest,
    db: Session = Depends(get_db),
    mongo_db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: User = Depends(get_current_user),
):
    """Set or update outbound and return flight references from the MongoDB catalogue."""
    trip = _get_user_trip(trip_id, db, current_user)
    itinerary = get_or_create_itinerary(trip, db)

    update_dict = payload.model_dump(exclude_unset=True)

    if "outbound_flight_id" in update_dict:
        val = update_dict["outbound_flight_id"]
        if val is not None and str(val).strip():
            f_str = str(val).strip()
            await validate_flight_id(f_str, mongo_db, label="Outbound flight")
            itinerary.outbound_flight_id = f_str
        else:
            itinerary.outbound_flight_id = None

    if "return_flight_id" in update_dict:
        val = update_dict["return_flight_id"]
        if val is not None and str(val).strip():
            f_str = str(val).strip()
            await validate_flight_id(f_str, mongo_db, label="Return flight")
            itinerary.return_flight_id = f_str
        else:
            itinerary.return_flight_id = None

    await recalculate_itinerary_cost(itinerary, trip, mongo_db, db=db)
    db.commit()
    db.refresh(itinerary)
    return itinerary


@router.put("/{trip_id}/activities", response_model=ItineraryResponse)
async def mutate_trip_activities(
    trip_id: int,
    payload: ActivityMutationRequest,
    db: Session = Depends(get_db),
    mongo_db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: User = Depends(get_current_user),
):
    """Add, remove, or replace scheduled activities in the trip itinerary."""
    trip = _get_user_trip(trip_id, db, current_user)
    itinerary = get_or_create_itinerary(trip, db)
    travellers = max(1, trip.travellers or 1)

    if payload.action == "add":
        if not payload.activity_id or not str(payload.activity_id).strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="activity_id is required to add an activity"
            )
        act_str = str(payload.activity_id).strip()
        act_doc = await validate_activity_id(act_str, mongo_db)

        cost = payload.estimated_cost
        if cost is None:
            cost = float(act_doc.get("price", 0.0)) * travellers

        new_item = ItineraryItem(
            itinerary_id=itinerary.id,
            day_number=payload.day_number or 1,
            time_slot=payload.time_slot,
            activity_id=act_str,
            title_override=payload.title_override,
            start_time=payload.start_time,
            duration_minutes=payload.duration_minutes or act_doc.get("duration_minutes"),
            estimated_cost=cost,
        )
        db.add(new_item)
        db.flush()

    elif payload.action == "remove":
        target_item = None
        if payload.item_id is not None:
            target_item = next((i for i in itinerary.items if i.id == payload.item_id), None)
        elif payload.activity_id:
            act_str = str(payload.activity_id).strip()
            target_item = next((i for i in itinerary.items if i.activity_id == act_str), None)

        if not target_item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Itinerary item not found to remove"
            )
        db.delete(target_item)
        db.flush()

    elif payload.action == "replace":
        if payload.items is not None:
            # Bulk replacement: remove existing and add supplied items
            for old_item in list(itinerary.items):
                db.delete(old_item)
            db.flush()

            for item_in in payload.items:
                act_doc = None
                act_str = None
                if item_in.activity_id and str(item_in.activity_id).strip():
                    act_str = str(item_in.activity_id).strip()
                    act_doc = await validate_activity_id(act_str, mongo_db)

                cost = item_in.estimated_cost
                if cost == 0.0 and act_doc:
                    cost = float(act_doc.get("price", 0.0)) * travellers

                created = ItineraryItem(
                    itinerary_id=itinerary.id,
                    day_number=item_in.day_number,
                    time_slot=item_in.time_slot,
                    activity_id=act_str,
                    title_override=item_in.title_override,
                    start_time=item_in.start_time,
                    duration_minutes=item_in.duration_minutes or (act_doc.get("duration_minutes") if act_doc else None),
                    estimated_cost=cost,
                )
                db.add(created)
            db.flush()

        elif payload.item_id is not None:
            target_item = next((i for i in itinerary.items if i.id == payload.item_id), None)
            if not target_item:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Itinerary item with ID '{payload.item_id}' not found"
                )
            if payload.activity_id:
                act_str = str(payload.activity_id).strip()
                act_doc = await validate_activity_id(act_str, mongo_db)
                target_item.activity_id = act_str
                if payload.estimated_cost is not None:
                    target_item.estimated_cost = payload.estimated_cost
                else:
                    target_item.estimated_cost = float(act_doc.get("price", 0.0)) * travellers
                if payload.duration_minutes:
                    target_item.duration_minutes = payload.duration_minutes
                elif act_doc.get("duration_minutes"):
                    target_item.duration_minutes = act_doc.get("duration_minutes")

            if payload.day_number is not None:
                target_item.day_number = payload.day_number
            if payload.time_slot is not None:
                target_item.time_slot = payload.time_slot
            if payload.title_override is not None:
                target_item.title_override = payload.title_override
            if payload.start_time is not None:
                target_item.start_time = payload.start_time
            db.flush()
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Either item_id or items list is required for replace action"
            )

    db.commit()
    db.refresh(itinerary)
    await recalculate_itinerary_cost(itinerary, trip, mongo_db, db=db)
    db.commit()
    db.refresh(itinerary)
    return itinerary


@router.post("/{trip_id}/generate", response_model=ItineraryGenerationResponse)
async def generate_trip_itinerary(
    trip_id: int,
    db: Session = Depends(get_db),
    mongo_db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: User = Depends(get_current_user),
):
    """
    Intelligently generate, score, schedule and persist a complete trip itinerary
    from MongoDB catalogue data, respecting trip pace, budget, and live weather.
    """
    trip = _get_user_trip(trip_id, db, current_user)
    return await generate_intelligent_itinerary(trip, db, mongo_db)
