from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from app.schemas.common import PaginatedResponse


class HotelBase(BaseModel):
    destination_id: str = Field(..., min_length=1, description="Associated Destination ID")
    name: str = Field(..., min_length=1, description="Hotel name")
    description: Optional[str] = Field(None, description="Hotel overview and facilities")
    address: Optional[str] = Field(None, description="Physical address")
    rating: float = Field(default=0.0, ge=0.0, le=5.0, description="Star rating between 0 and 5")
    price_per_night: float = Field(..., ge=0.0, description="Price per room night")
    currency: str = Field(default="INR", description="Currency code (e.g. INR, USD)")
    amenities: List[str] = Field(default_factory=list, description="Available amenities (e.g. WiFi, Pool)")
    image_urls: List[str] = Field(default_factory=list, description="Image URLs of property")
    latitude: Optional[float] = Field(None, ge=-90.0, le=90.0, description="Latitude coordinate")
    longitude: Optional[float] = Field(None, ge=-180.0, le=180.0, description="Longitude coordinate")
    available_rooms: int = Field(default=0, ge=0, description="Number of currently available rooms")


class HotelCreate(HotelBase):
    pass


class HotelUpdate(BaseModel):
    destination_id: Optional[str] = Field(None, min_length=1)
    name: Optional[str] = Field(None, min_length=1)
    description: Optional[str] = None
    address: Optional[str] = None
    rating: Optional[float] = Field(None, ge=0.0, le=5.0)
    price_per_night: Optional[float] = Field(None, ge=0.0)
    currency: Optional[str] = None
    amenities: Optional[List[str]] = None
    image_urls: Optional[List[str]] = None
    latitude: Optional[float] = Field(None, ge=-90.0, le=90.0)
    longitude: Optional[float] = Field(None, ge=-180.0, le=180.0)
    available_rooms: Optional[int] = Field(None, ge=0)


class HotelResponse(HotelBase):
    id: str = Field(..., description="Stringified MongoDB ObjectId")
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": "60c72b2f9b1d8b2bad8d3b82",
                "destination_id": "60c72b2f9b1d8b2bad8d3b71",
                "name": "Heritage Palace Resort",
                "description": "Luxury heritage hotel with royal courtyards and spa.",
                "address": "MI Road, Jaipur, Rajasthan",
                "rating": 4.8,
                "price_per_night": 4500.0,
                "currency": "INR",
                "amenities": ["WiFi", "Swimming Pool", "Spa", "Breakfast"],
                "image_urls": ["https://images.unsplash.com/photo-hotel"],
                "latitude": 26.9150,
                "longitude": 75.7900,
                "available_rooms": 12,
                "created_at": "2026-01-01T00:00:00Z",
                "updated_at": "2026-01-01T00:00:00Z"
            }
        }
    }


HotelListResponse = PaginatedResponse[HotelResponse]
