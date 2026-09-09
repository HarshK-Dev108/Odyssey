from datetime import datetime, timezone
import math
import re
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from sqlalchemy.orm import Session

from app.core.mongodb import get_database, is_valid_object_id, str_to_object_id, serialize_doc
from app.core.auth import get_current_user
from app.core.database import get_db
from app.models.trip import Trip
from app.models.user import User
from app.schemas.expense import (
    ExpenseCreate,
    ExpenseUpdate,
    ExpenseResponse,
    ExpenseListResponse,
    ExpenseSummaryResponse
)

router = APIRouter(
    prefix="/expenses",
    tags=["Expenses"]
)

COLLECTION_NAME = "expenses"


def _require_owned_trip(trip_id: int, db: Session, user: User) -> Trip:
    trip = db.query(Trip).filter(
        Trip.id == trip_id,
        Trip.user_id == user.id,
    ).first()

    if trip is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trip not found",
        )

    return trip


async def _get_owned_expense(
    expense_id: str,
    mongo_db: AsyncIOMotorDatabase,
    sql_db: Session,
    user: User,
) -> dict:
    if not is_valid_object_id(expense_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid expense ID format: '{expense_id}'",
        )

    document = await mongo_db[COLLECTION_NAME].find_one(
        {"_id": str_to_object_id(expense_id)}
    )
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Expense with ID '{expense_id}' not found",
        )

    _require_owned_trip(document.get("trip_id"), sql_db, user)
    return document


@router.get(
    "/summary",
    response_model=ExpenseSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get aggregated expense summary",
    description="Calculates total expenses and category breakdowns, optionally filtered by trip_id."
)
async def get_expense_summary(
    trip_id: Optional[int] = Query(None, description="Filter summary by SQLite Trip ID"),
    db: AsyncIOMotorDatabase = Depends(get_database),
    sql_db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ExpenseSummaryResponse:
    match_stage = {}
    if trip_id is not None:
        _require_owned_trip(trip_id, sql_db, current_user)
        match_stage["trip_id"] = trip_id
    else:
        owned_trip_ids = [
            trip.id
            for trip in sql_db.query(Trip.id).filter(
                Trip.user_id == current_user.id
            ).all()
        ]
        match_stage["trip_id"] = {"$in": owned_trip_ids}

    pipeline = []
    if match_stage:
        pipeline.append({"$match": match_stage})

    pipeline.append({
        "$group": {
            "_id": "$category",
            "total": {"$sum": "$amount"},
            "count": {"$sum": 1}
        }
    })

    cursor = db[COLLECTION_NAME].aggregate(pipeline)
    by_category = {}
    total_amount = 0.0
    total_count = 0

    async for doc in cursor:
        cat = doc["_id"] or "Uncategorized"
        amount = float(doc["total"])
        count = int(doc["count"])
        by_category[cat] = round(amount, 2)
        total_amount += amount
        total_count += count

    return ExpenseSummaryResponse(
        trip_id=trip_id,
        total_expenses=total_count,
        total_amount=round(total_amount, 2),
        currency="INR",
        by_category=by_category
    )


@router.get(
    "",
    response_model=ExpenseListResponse,
    status_code=status.HTTP_200_OK,
    summary="List and filter expenses",
    description="Retrieve paginated expense records with optional filters for trip_id and category."
)
async def list_expenses(
    trip_id: Optional[int] = Query(None, description="Filter expenses by SQLite Trip ID"),
    category: Optional[str] = Query(None, description="Filter by category (Food, Stay, Travel, etc.)"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    db: AsyncIOMotorDatabase = Depends(get_database),
    sql_db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ExpenseListResponse:
    query = {}

    if trip_id is not None:
        _require_owned_trip(trip_id, sql_db, current_user)
        query["trip_id"] = trip_id
    else:
        owned_trip_ids = [
            trip.id
            for trip in sql_db.query(Trip.id).filter(
                Trip.user_id == current_user.id
            ).all()
        ]
        query["trip_id"] = {"$in": owned_trip_ids}

    if category:
        query["category"] = {"$regex": f"^{re.escape(category.strip())}$", "$options": "i"}

    collection = db[COLLECTION_NAME]
    total = await collection.count_documents(query)
    total_pages = math.ceil(total / limit) if total > 0 else 0

    skip = (page - 1) * limit
    cursor = collection.find(query).skip(skip).limit(limit).sort("expense_date", -1)
    docs = await cursor.to_list(length=limit)

    items = [ExpenseResponse(**serialize_doc(doc)) for doc in docs]

    return ExpenseListResponse(
        items=items,
        total=total,
        page=page,
        limit=limit,
        total_pages=total_pages
    )


@router.get(
    "/{id}",
    response_model=ExpenseResponse,
    status_code=status.HTTP_200_OK,
    summary="Get expense by ID",
    description="Retrieve an expense record by its MongoDB ObjectId."
)
async def get_expense(
    id: str,
    db: AsyncIOMotorDatabase = Depends(get_database),
    sql_db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ExpenseResponse:
    doc = await _get_owned_expense(id, db, sql_db, current_user)

    return ExpenseResponse(**serialize_doc(doc))


@router.post(
    "",
    response_model=ExpenseResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new expense",
    description="Log an expense for a trip."
)
async def create_expense(
    payload: ExpenseCreate,
    db: AsyncIOMotorDatabase = Depends(get_database),
    sql_db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ExpenseResponse:
    _require_owned_trip(payload.trip_id, sql_db, current_user)
    now = datetime.now(timezone.utc)
    doc_data = payload.model_dump()
    # Serialize date to isoformat string or datetime for mongo
    if hasattr(doc_data.get("expense_date"), "isoformat"):
        doc_data["expense_date"] = doc_data["expense_date"].isoformat()
    doc_data["created_at"] = now

    result = await db[COLLECTION_NAME].insert_one(doc_data)
    doc_data["_id"] = result.inserted_id

    return ExpenseResponse(**serialize_doc(doc_data))


@router.put(
    "/{id}",
    response_model=ExpenseResponse,
    status_code=status.HTTP_200_OK,
    summary="Update an expense",
    description="Modify an existing expense entry."
)
async def update_expense(
    id: str,
    payload: ExpenseUpdate,
    db: AsyncIOMotorDatabase = Depends(get_database),
    sql_db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ExpenseResponse:
    existing = await _get_owned_expense(id, db, sql_db, current_user)

    update_fields = {k: v for k, v in payload.model_dump(exclude_unset=True).items()}
    if not update_fields:
        return ExpenseResponse(**serialize_doc(existing))

    if "trip_id" in update_fields:
        _require_owned_trip(update_fields["trip_id"], sql_db, current_user)

    if "expense_date" in update_fields and hasattr(update_fields["expense_date"], "isoformat"):
        update_fields["expense_date"] = update_fields["expense_date"].isoformat()

    result = await db[COLLECTION_NAME].find_one_and_update(
        {"_id": str_to_object_id(id)},
        {"$set": update_fields},
        return_document=True
    )

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Expense with ID '{id}' not found"
        )

    return ExpenseResponse(**serialize_doc(result))


@router.delete(
    "/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an expense",
    description="Remove an expense record by ID."
)
async def delete_expense(
    id: str,
    db: AsyncIOMotorDatabase = Depends(get_database),
    sql_db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    await _get_owned_expense(id, db, sql_db, current_user)

    result = await db[COLLECTION_NAME].delete_one({"_id": str_to_object_id(id)})
    if result.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Expense with ID '{id}' not found"
        )
