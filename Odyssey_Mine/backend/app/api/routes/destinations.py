from datetime import datetime, timezone
import math
import re
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.mongodb import get_database, is_valid_object_id, str_to_object_id, serialize_doc
from app.schemas.destination import (
    DestinationCreate,
    DestinationUpdate,
    DestinationResponse,
    DestinationListResponse
)

router = APIRouter(
    prefix="/destinations",
    tags=["Destinations"]
)

COLLECTION_NAME = "destinations"


@router.get(
    "",
    response_model=DestinationListResponse,
    status_code=status.HTTP_200_OK,
    summary="List and search destinations",
    description="Retrieve paginated destinations with optional text search and country filtering."
)
async def list_destinations(
    search: Optional[str] = Query(None, description="Search keyword matching name, city, state, or tags"),
    country: Optional[str] = Query(None, description="Filter by country"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    db: AsyncIOMotorDatabase = Depends(get_database)
) -> DestinationListResponse:
    query = {}

    if country:
        query["country"] = {"$regex": f"^{re.escape(country.strip())}$", "$options": "i"}

    if search:
        s = re.escape(search.strip())
        query["$or"] = [
            {"name": {"$regex": s, "$options": "i"}},
            {"city": {"$regex": s, "$options": "i"}},
            {"state": {"$regex": s, "$options": "i"}},
            {"tags": {"$regex": s, "$options": "i"}},
            {"description": {"$regex": s, "$options": "i"}}
        ]

    collection = db[COLLECTION_NAME]
    total = await collection.count_documents(query)
    total_pages = math.ceil(total / limit) if total > 0 else 0

    skip = (page - 1) * limit
    cursor = collection.find(query).skip(skip).limit(limit).sort("name", 1)
    docs = await cursor.to_list(length=limit)

    items = [DestinationResponse(**serialize_doc(doc)) for doc in docs]

    return DestinationListResponse(
        items=items,
        total=total,
        page=page,
        limit=limit,
        total_pages=total_pages
    )


@router.get(
    "/{id}",
    response_model=DestinationResponse,
    status_code=status.HTTP_200_OK,
    summary="Get destination by ID",
    description="Retrieve a single destination record using its MongoDB ObjectId."
)
async def get_destination(
    id: str,
    db: AsyncIOMotorDatabase = Depends(get_database)
) -> DestinationResponse:
    if not is_valid_object_id(id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid destination ID format: '{id}'"
        )

    doc = await db[COLLECTION_NAME].find_one({"_id": str_to_object_id(id)})
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Destination with ID '{id}' not found"
        )

    return DestinationResponse(**serialize_doc(doc))


@router.post(
    "",
    response_model=DestinationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new destination",
    description="Create a new destination record in the database."
)
async def create_destination(
    payload: DestinationCreate,
    db: AsyncIOMotorDatabase = Depends(get_database)
) -> DestinationResponse:
    now = datetime.now(timezone.utc)
    doc_data = payload.model_dump()
    doc_data["created_at"] = now
    doc_data["updated_at"] = now

    result = await db[COLLECTION_NAME].insert_one(doc_data)
    doc_data["_id"] = result.inserted_id

    return DestinationResponse(**serialize_doc(doc_data))


@router.put(
    "/{id}",
    response_model=DestinationResponse,
    status_code=status.HTTP_200_OK,
    summary="Update a destination",
    description="Modify an existing destination record."
)
async def update_destination(
    id: str,
    payload: DestinationUpdate,
    db: AsyncIOMotorDatabase = Depends(get_database)
) -> DestinationResponse:
    if not is_valid_object_id(id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid destination ID format: '{id}'"
        )

    update_fields = {k: v for k, v in payload.model_dump(exclude_unset=True).items()}
    if not update_fields:
        doc = await db[COLLECTION_NAME].find_one({"_id": str_to_object_id(id)})
        if not doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Destination with ID '{id}' not found"
            )
        return DestinationResponse(**serialize_doc(doc))

    update_fields["updated_at"] = datetime.now(timezone.utc)

    result = await db[COLLECTION_NAME].find_one_and_update(
        {"_id": str_to_object_id(id)},
        {"$set": update_fields},
        return_document=True
    )

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Destination with ID '{id}' not found"
        )

    return DestinationResponse(**serialize_doc(result))


@router.delete(
    "/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a destination",
    description="Remove an existing destination record by ID."
)
async def delete_destination(
    id: str,
    db: AsyncIOMotorDatabase = Depends(get_database)
) -> None:
    if not is_valid_object_id(id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid destination ID format: '{id}'"
        )

    result = await db[COLLECTION_NAME].delete_one({"_id": str_to_object_id(id)})
    if result.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Destination with ID '{id}' not found"
        )
