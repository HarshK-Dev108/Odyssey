from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from app.schemas.common import PaginatedResponse


class FlightBase(BaseModel):
    origin: str = Field(..., min_length=2, description="Departure airport or city code")
    destination: str = Field(..., min_length=2, description="Arrival airport or city code")
    airline: str = Field(..., min_length=1, description="Operating airline name")
    flight_number: str = Field(..., min_length=1, description="Flight identifier number")
    departure_time: datetime = Field(..., description="Scheduled departure timestamp")
    arrival_time: datetime = Field(..., description="Scheduled arrival timestamp")
    duration_minutes: int = Field(..., gt=0, description="Flight duration in minutes")
    price: float = Field(..., ge=0.0, description="Ticket fare price")
    currency: str = Field(default="INR", description="Currency code")
    stops: int = Field(default=0, ge=0, description="Number of layovers/stops")
    available_seats: int = Field(default=0, ge=0, description="Number of available seats")


class FlightCreate(FlightBase):
    pass


class FlightUpdate(BaseModel):
    origin: Optional[str] = Field(None, min_length=2)
    destination: Optional[str] = Field(None, min_length=2)
    airline: Optional[str] = Field(None, min_length=1)
    flight_number: Optional[str] = Field(None, min_length=1)
    departure_time: Optional[datetime] = None
    arrival_time: Optional[datetime] = None
    duration_minutes: Optional[int] = Field(None, gt=0)
    price: Optional[float] = Field(None, ge=0.0)
    currency: Optional[str] = None
    stops: Optional[int] = Field(None, ge=0)
    available_seats: Optional[int] = Field(None, ge=0)


class FlightResponse(FlightBase):
    id: str = Field(..., description="Stringified MongoDB ObjectId")
    created_at: datetime

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": "60c72b2f9b1d8b2bad8d3b93",
                "origin": "DEL",
                "destination": "JAI",
                "airline": "IndiGo",
                "flight_number": "6E-205",
                "departure_time": "2026-03-15T08:00:00Z",
                "arrival_time": "2026-03-15T09:00:00Z",
                "duration_minutes": 60,
                "price": 2800.0,
                "currency": "INR",
                "stops": 0,
                "available_seats": 25,
                "created_at": "2026-01-01T00:00:00Z"
            }
        }
    }


FlightListResponse = PaginatedResponse[FlightResponse]
