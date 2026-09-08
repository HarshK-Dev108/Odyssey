from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from app.schemas.common import PaginatedResponse


class ActivityBase(BaseModel):
    destination_id: str = Field(..., min_length=1, description="Associated Destination ID")
    name: str = Field(..., min_length=1, description="Activity name")
    description: Optional[str] = Field(None, description="Detailed description of experience")
    category: str = Field(default="Sightseeing", description="Category (e.g. Adventure, Heritage, Food)")
    duration_minutes: int = Field(..., gt=0, description="Duration in minutes")
    price: float = Field(..., ge=0.0, description="Cost per participant")
    currency: str = Field(default="INR", description="Currency code")
    rating: float = Field(default=0.0, ge=0.0, le=5.0, description="Rating from 0 to 5")
    image_url: Optional[str] = Field(None, description="Image URL")
    location: Optional[str] = Field(None, description="Specific location or meeting point")


class ActivityCreate(ActivityBase):
    pass


class ActivityUpdate(BaseModel):
    destination_id: Optional[str] = Field(None, min_length=1)
    name: Optional[str] = Field(None, min_length=1)
    description: Optional[str] = None
    category: Optional[str] = None
    duration_minutes: Optional[int] = Field(None, gt=0)
    price: Optional[float] = Field(None, ge=0.0)
    currency: Optional[str] = None
    rating: Optional[float] = Field(None, ge=0.0, le=5.0)
    image_url: Optional[str] = None
    location: Optional[str] = None


class ActivityResponse(ActivityBase):
    id: str = Field(..., description="Stringified MongoDB ObjectId")
    created_at: datetime

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": "60c72b2f9b1d8b2bad8d3ba4",
                "destination_id": "60c72b2f9b1d8b2bad8d3b71",
                "name": "Amber Fort Guided Tour & Light Show",
                "description": "Historical walking tour exploring palaces, courtyards and evening light show.",
                "category": "Heritage",
                "duration_minutes": 180,
                "price": 750.0,
                "currency": "INR",
                "rating": 4.7,
                "image_url": "https://images.unsplash.com/photo-amber-fort",
                "location": "Amer, Jaipur",
                "created_at": "2026-01-01T00:00:00Z"
            }
        }
    }


ActivityListResponse = PaginatedResponse[ActivityResponse]
