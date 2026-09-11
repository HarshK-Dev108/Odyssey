from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from app.schemas.common import PaginatedResponse


class DestinationBase(BaseModel):
    name: str = Field(..., min_length=1, description="Destination name")
    country: str = Field(..., min_length=1, description="Country name")
    state: Optional[str] = Field(None, description="State or province")
    city: Optional[str] = Field(None, description="City name")
    description: Optional[str] = Field(None, description="Destination overview")
    image_url: Optional[str] = Field(None, description="Cover image URL")
    latitude: Optional[float] = Field(None, ge=-90.0, le=90.0, description="Latitude coordinate")
    longitude: Optional[float] = Field(None, ge=-180.0, le=180.0, description="Longitude coordinate")
    tags: List[str] = Field(default_factory=list, description="Categorical tags")
    best_time_to_visit: Optional[str] = Field(None, description="Optimal travel seasons")


class DestinationCreate(DestinationBase):
    pass


class DestinationUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1)
    country: Optional[str] = Field(None, min_length=1)
    state: Optional[str] = None
    city: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    latitude: Optional[float] = Field(None, ge=-90.0, le=90.0)
    longitude: Optional[float] = Field(None, ge=-180.0, le=180.0)
    tags: Optional[List[str]] = None
    best_time_to_visit: Optional[str] = None


class DestinationResponse(DestinationBase):
    id: str = Field(..., description="Stringified MongoDB ObjectId")
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": "60c72b2f9b1d8b2bad8d3b71",
                "name": "Jaipur",
                "country": "India",
                "state": "Rajasthan",
                "city": "Jaipur",
                "description": "The Pink City, famous for its historic palaces and forts.",
                "image_url": "https://images.unsplash.com/photo-jaipur",
                "latitude": 26.9124,
                "longitude": 75.7873,
                "tags": ["culture", "heritage", "palaces"],
                "best_time_to_visit": "October to March",
                "created_at": "2026-01-01T00:00:00Z",
                "updated_at": "2026-01-01T00:00:00Z"
            }
        }
    }


DestinationListResponse = PaginatedResponse[DestinationResponse]
