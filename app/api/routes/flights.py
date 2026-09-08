from datetime import datetime, timezone
import math
import re
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.mongodb import get_database, is_valid_object_id, str_to_object_id, serialize_doc
from app.schemas.flight import (
    FlightCreate,
    FlightUpdate,
    FlightResponse,
    FlightListResponse
)

router = APIRouter(
    prefix="/flights",
    tags=["Flights"]
)

COLLECTION_NAME = "flights"


@router.get(
    "",
    response_model=FlightListResponse,
    status_code=status.HTTP_200_OK,
    summary="List and filter flight schedules",
    description="Retrieve paginated flights with filters for origin, destination, airline, and price range."
)
async def list_flights(
    origin: Optional[str] = Query(None, description="Origin airport or city code (e.g. DEL, BOM)"),
    destination: Optional[str] = Query(None, description="Destination airport or city code (e.g. GOI, JAI)"),
    airline: Optional[str] = Query(None, description="Filter by airline name"),
    min_price: Optional[float] = Query(None, ge=0.0, description="Minimum price"),
    max_price: Optional[float] = Query(None, ge=0.0, description="Maximum price"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    db: AsyncIOMotorDatabase = Depends(get_database)
) -> FlightListResponse:
    query = {}

    if origin:
        query["origin"] = {"$regex": f"^{re.escape(origin.strip())}$", "$options": "i"}

    if destination:
        query["destination"] = {"$regex": f"^{re.escape(destination.strip())}$", "$options": "i"}

    if airline:
        query["airline"] = {"$regex": re.escape(airline.strip()), "$options": "i"}

    price_filter = {}
    if min_price is not None:
        price_filter["$gte"] = min_price
    if max_price is not None:
        price_filter["$lte"] = max_price
    if price_filter:
        query["price"] = price_filter

    collection = db[COLLECTION_NAME]
    total = await collection.count_documents(query)
    total_pages = math.ceil(total / limit) if total > 0 else 0

    skip = (page - 1) * limit
    cursor = collection.find(query).skip(skip).limit(limit).sort("price", 1)
    docs = await cursor.to_list(length=limit)

    items = [FlightResponse(**serialize_doc(doc)) for doc in docs]

    return FlightListResponse(
        items=items,
        total=total,
        page=page,
        limit=limit,
        total_pages=total_pages
    )


@router.get(
    "/{id}",
    response_model=FlightResponse,
    status_code=status.HTTP_200_OK,
    summary="Get flight by ID",
    description="Retrieve a flight record by its MongoDB ObjectId."
)
async def get_flight(
    id: str,
    db: AsyncIOMotorDatabase = Depends(get_database)
) -> FlightResponse:
    if not is_valid_object_id(id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid flight ID format: '{id}'"
        )

    doc = await db[COLLECTION_NAME].find_one({"_id": str_to_object_id(id)})
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Flight with ID '{id}' not found"
        )

    return FlightResponse(**serialize_doc(doc))


@router.post(
    "",
    response_model=FlightResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new flight schedule",
    description="Add a new flight offering."
)
async def create_flight(
    payload: FlightCreate,
    db: AsyncIOMotorDatabase = Depends(get_database)
) -> FlightResponse:
    now = datetime.now(timezone.utc)
    doc_data = payload.model_dump()
    doc_data["created_at"] = now

    result = await db[COLLECTION_NAME].insert_one(doc_data)
    doc_data["_id"] = result.inserted_id

    return FlightResponse(**serialize_doc(doc_data))


@router.put(
    "/{id}",
    response_model=FlightResponse,
    status_code=status.HTTP_200_OK,
    summary="Update a flight schedule",
    description="Modify an existing flight record."
)
async def update_flight(
    id: str,
    payload: FlightUpdate,
    db: AsyncIOMotorDatabase = Depends(get_database)
) -> FlightResponse:
    if not is_valid_object_id(id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid flight ID format: '{id}'"
        )

    update_fields = {k: v for k, v in payload.model_dump(exclude_unset=True).items()}
    if not update_fields:
        doc = await db[COLLECTION_NAME].find_one({"_id": str_to_object_id(id)})
        if not doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Flight with ID '{id}' not found"
            )
        return FlightResponse(**serialize_doc(doc))

    result = await db[COLLECTION_NAME].find_one_and_update(
        {"_id": str_to_object_id(id)},
        {"$set": update_fields},
        return_document=True
    )

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Flight with ID '{id}' not found"
        )

    return FlightResponse(**serialize_doc(result))


@router.delete(
    "/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a flight schedule",
    description="Remove a flight record by ID."
)
async def delete_flight(
    id: str,
    db: AsyncIOMotorDatabase = Depends(get_database)
) -> None:
    if not is_valid_object_id(id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid flight ID format: '{id}'"
        )

    result = await db[COLLECTION_NAME].delete_one({"_id": str_to_object_id(id)})
    if result.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Flight with ID '{id}' not found"
        )
