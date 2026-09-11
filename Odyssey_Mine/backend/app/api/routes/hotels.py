from datetime import datetime, timezone
import math
import re
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.mongodb import get_database, is_valid_object_id, str_to_object_id, serialize_doc
from app.schemas.hotel import (
    HotelCreate,
    HotelUpdate,
    HotelResponse,
    HotelListResponse
)

router = APIRouter(
    prefix="/hotels",
    tags=["Hotels"]
)

COLLECTION_NAME = "hotels"


@router.get(
    "",
    response_model=HotelListResponse,
    status_code=status.HTTP_200_OK,
    summary="List and filter hotels",
    description="Retrieve paginated hotels with filters for destination, price range, min rating, and keyword search."
)
async def list_hotels(
    destination_id: Optional[str] = Query(None, description="Filter by associated destination ID"),
    search: Optional[str] = Query(None, description="Keyword search in hotel name, address, or amenities"),
    min_price: Optional[float] = Query(None, ge=0.0, description="Minimum price per night"),
    max_price: Optional[float] = Query(None, ge=0.0, description="Maximum price per night"),
    min_rating: Optional[float] = Query(None, ge=0.0, le=5.0, description="Minimum star rating (0-5)"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    db: AsyncIOMotorDatabase = Depends(get_database)
) -> HotelListResponse:
    query = {}

    if destination_id:
        query["destination_id"] = destination_id.strip()

    if search:
        s = re.escape(search.strip())
        query["$or"] = [
            {"name": {"$regex": s, "$options": "i"}},
            {"address": {"$regex": s, "$options": "i"}},
            {"amenities": {"$regex": s, "$options": "i"}},
            {"description": {"$regex": s, "$options": "i"}}
        ]

    price_filter = {}
    if min_price is not None:
        price_filter["$gte"] = min_price
    if max_price is not None:
        price_filter["$lte"] = max_price
    if price_filter:
        query["price_per_night"] = price_filter

    if min_rating is not None:
        query["rating"] = {"$gte": min_rating}

    collection = db[COLLECTION_NAME]
    total = await collection.count_documents(query)
    total_pages = math.ceil(total / limit) if total > 0 else 0

    skip = (page - 1) * limit
    cursor = collection.find(query).skip(skip).limit(limit).sort("rating", -1)
    docs = await cursor.to_list(length=limit)

    items = [HotelResponse(**serialize_doc(doc)) for doc in docs]

    return HotelListResponse(
        items=items,
        total=total,
        page=page,
        limit=limit,
        total_pages=total_pages
    )


@router.get(
    "/{id}",
    response_model=HotelResponse,
    status_code=status.HTTP_200_OK,
    summary="Get hotel by ID",
    description="Retrieve a single hotel record by its MongoDB ObjectId."
)
async def get_hotel(
    id: str,
    db: AsyncIOMotorDatabase = Depends(get_database)
) -> HotelResponse:
    if not is_valid_object_id(id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid hotel ID format: '{id}'"
        )

    doc = await db[COLLECTION_NAME].find_one({"_id": str_to_object_id(id)})
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Hotel with ID '{id}' not found"
        )

    return HotelResponse(**serialize_doc(doc))


@router.post(
    "",
    response_model=HotelResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new hotel",
    description="Add a new accommodation listing."
)
async def create_hotel(
    payload: HotelCreate,
    db: AsyncIOMotorDatabase = Depends(get_database)
) -> HotelResponse:
    now = datetime.now(timezone.utc)
    doc_data = payload.model_dump()
    doc_data["created_at"] = now
    doc_data["updated_at"] = now

    result = await db[COLLECTION_NAME].insert_one(doc_data)
    doc_data["_id"] = result.inserted_id

    return HotelResponse(**serialize_doc(doc_data))


@router.put(
    "/{id}",
    response_model=HotelResponse,
    status_code=status.HTTP_200_OK,
    summary="Update a hotel",
    description="Modify an existing hotel record."
)
async def update_hotel(
    id: str,
    payload: HotelUpdate,
    db: AsyncIOMotorDatabase = Depends(get_database)
) -> HotelResponse:
    if not is_valid_object_id(id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid hotel ID format: '{id}'"
        )

    update_fields = {k: v for k, v in payload.model_dump(exclude_unset=True).items()}
    if not update_fields:
        doc = await db[COLLECTION_NAME].find_one({"_id": str_to_object_id(id)})
        if not doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Hotel with ID '{id}' not found"
            )
        return HotelResponse(**serialize_doc(doc))

    update_fields["updated_at"] = datetime.now(timezone.utc)

    result = await db[COLLECTION_NAME].find_one_and_update(
        {"_id": str_to_object_id(id)},
        {"$set": update_fields},
        return_document=True
    )

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Hotel with ID '{id}' not found"
        )

    return HotelResponse(**serialize_doc(result))


@router.delete(
    "/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a hotel",
    description="Remove a hotel listing by ID."
)
async def delete_hotel(
    id: str,
    db: AsyncIOMotorDatabase = Depends(get_database)
) -> None:
    if not is_valid_object_id(id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid hotel ID format: '{id}'"
        )

    result = await db[COLLECTION_NAME].delete_one({"_id": str_to_object_id(id)})
    if result.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Hotel with ID '{id}' not found"
        )
