from datetime import datetime, timezone
import math
import re
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.mongodb import get_database, is_valid_object_id, str_to_object_id, serialize_doc
from app.schemas.activity import (
    ActivityCreate,
    ActivityUpdate,
    ActivityResponse,
    ActivityListResponse
)

router = APIRouter(
    prefix="/activities",
    tags=["Activities"]
)

COLLECTION_NAME = "activities"


@router.get(
    "",
    response_model=ActivityListResponse,
    status_code=status.HTTP_200_OK,
    summary="List and filter activities",
    description="Retrieve paginated tourism experiences and activities with flexible filters."
)
async def list_activities(
    destination_id: Optional[str] = Query(None, description="Filter by destination ID"),
    category: Optional[str] = Query(None, description="Filter by category (e.g. Adventure, Heritage, Food)"),
    search: Optional[str] = Query(None, description="Keyword search in activity name, description, or location"),
    min_price: Optional[float] = Query(None, ge=0.0, description="Minimum activity price"),
    max_price: Optional[float] = Query(None, ge=0.0, description="Maximum activity price"),
    min_rating: Optional[float] = Query(None, ge=0.0, le=5.0, description="Minimum rating (0-5)"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    db: AsyncIOMotorDatabase = Depends(get_database)
) -> ActivityListResponse:
    query = {}

    if destination_id:
        query["destination_id"] = destination_id.strip()

    if category:
        query["category"] = {"$regex": f"^{re.escape(category.strip())}$", "$options": "i"}

    if search:
        s = re.escape(search.strip())
        query["$or"] = [
            {"name": {"$regex": s, "$options": "i"}},
            {"description": {"$regex": s, "$options": "i"}},
            {"location": {"$regex": s, "$options": "i"}},
            {"category": {"$regex": s, "$options": "i"}}
        ]

    price_filter = {}
    if min_price is not None:
        price_filter["$gte"] = min_price
    if max_price is not None:
        price_filter["$lte"] = max_price
    if price_filter:
        query["price"] = price_filter

    if min_rating is not None:
        query["rating"] = {"$gte": min_rating}

    collection = db[COLLECTION_NAME]
    total = await collection.count_documents(query)
    total_pages = math.ceil(total / limit) if total > 0 else 0

    skip = (page - 1) * limit
    cursor = collection.find(query).skip(skip).limit(limit).sort("rating", -1)
    docs = await cursor.to_list(length=limit)

    items = [ActivityResponse(**serialize_doc(doc)) for doc in docs]

    return ActivityListResponse(
        items=items,
        total=total,
        page=page,
        limit=limit,
        total_pages=total_pages
    )


@router.get(
    "/{id}",
    response_model=ActivityResponse,
    status_code=status.HTTP_200_OK,
    summary="Get activity by ID",
    description="Retrieve a single activity record by its MongoDB ObjectId."
)
async def get_activity(
    id: str,
    db: AsyncIOMotorDatabase = Depends(get_database)
) -> ActivityResponse:
    if not is_valid_object_id(id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid activity ID format: '{id}'"
        )

    doc = await db[COLLECTION_NAME].find_one({"_id": str_to_object_id(id)})
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Activity with ID '{id}' not found"
        )

    return ActivityResponse(**serialize_doc(doc))


@router.post(
    "",
    response_model=ActivityResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new activity",
    description="Add a new tourism experience or activity."
)
async def create_activity(
    payload: ActivityCreate,
    db: AsyncIOMotorDatabase = Depends(get_database)
) -> ActivityResponse:
    now = datetime.now(timezone.utc)
    doc_data = payload.model_dump()
    doc_data["created_at"] = now

    result = await db[COLLECTION_NAME].insert_one(doc_data)
    doc_data["_id"] = result.inserted_id

    return ActivityResponse(**serialize_doc(doc_data))


@router.put(
    "/{id}",
    response_model=ActivityResponse,
    status_code=status.HTTP_200_OK,
    summary="Update an activity",
    description="Modify an existing activity record."
)
async def update_activity(
    id: str,
    payload: ActivityUpdate,
    db: AsyncIOMotorDatabase = Depends(get_database)
) -> ActivityResponse:
    if not is_valid_object_id(id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid activity ID format: '{id}'"
        )

    update_fields = {k: v for k, v in payload.model_dump(exclude_unset=True).items()}
    if not update_fields:
        doc = await db[COLLECTION_NAME].find_one({"_id": str_to_object_id(id)})
        if not doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Activity with ID '{id}' not found"
            )
        return ActivityResponse(**serialize_doc(doc))

    result = await db[COLLECTION_NAME].find_one_and_update(
        {"_id": str_to_object_id(id)},
        {"$set": update_fields},
        return_document=True
    )

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Activity with ID '{id}' not found"
        )

    return ActivityResponse(**serialize_doc(result))


@router.delete(
    "/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an activity",
    description="Remove an activity listing by ID."
)
async def delete_activity(
    id: str,
    db: AsyncIOMotorDatabase = Depends(get_database)
) -> None:
    if not is_valid_object_id(id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid activity ID format: '{id}'"
        )

    result = await db[COLLECTION_NAME].delete_one({"_id": str_to_object_id(id)})
    if result.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Activity with ID '{id}' not found"
        )
