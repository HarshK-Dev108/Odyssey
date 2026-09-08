from datetime import datetime, date
from typing import Optional, Dict
from pydantic import BaseModel, Field
from app.schemas.common import PaginatedResponse


class ExpenseBase(BaseModel):
    trip_id: int = Field(..., description="External scalar reference to SQLite Trip ID")
    category: str = Field(default="Other", description="Expense category (Food, Stay, Travel, Activities, etc.)")
    title: str = Field(..., min_length=1, description="Expense description or title")
    amount: float = Field(..., ge=0.0, description="Amount spent (non-negative)")
    currency: str = Field(default="INR", description="Currency code")
    expense_date: date = Field(default_factory=date.today, description="Date when expense was incurred")
    notes: Optional[str] = Field(None, description="Additional notes or receipt info")


class ExpenseCreate(ExpenseBase):
    pass


class ExpenseUpdate(BaseModel):
    trip_id: Optional[int] = None
    category: Optional[str] = None
    title: Optional[str] = Field(None, min_length=1)
    amount: Optional[float] = Field(None, ge=0.0)
    currency: Optional[str] = None
    expense_date: Optional[date] = None
    notes: Optional[str] = None


class ExpenseResponse(ExpenseBase):
    id: str = Field(..., description="Stringified MongoDB ObjectId")
    created_at: datetime

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": "60c72b2f9b1d8b2bad8d3bb5",
                "trip_id": 1,
                "category": "Food",
                "title": "Rajasthani Thali Dinner",
                "amount": 1200.0,
                "currency": "INR",
                "expense_date": "2026-03-15",
                "notes": "Chokhi Dhani traditional dinner",
                "created_at": "2026-01-01T00:00:00Z"
            }
        }
    }


class ExpenseSummaryResponse(BaseModel):
    trip_id: Optional[int] = None
    total_expenses: int = Field(..., ge=0, description="Count of expenses")
    total_amount: float = Field(..., ge=0.0, description="Sum of all expenses")
    currency: str = Field(default="INR", description="Primary currency")
    by_category: Dict[str, float] = Field(default_factory=dict, description="Category-wise expense breakdown")


ExpenseListResponse = PaginatedResponse[ExpenseResponse]
