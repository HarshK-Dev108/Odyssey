from datetime import date

from pydantic import BaseModel, Field


class TripRequest(BaseModel):
    from_city: str = Field(..., min_length=2)
    destination: str = Field(..., min_length=2)

    start_date: date
    end_date: date

    travellers: int = Field(..., ge=1)
    budget: float = Field(..., gt=0)

    currency: str = "INR"

    interests: list[str] = []

    hotel_rating: int = Field(default=3, ge=1, le=5)
    pace: str = "moderate"
    avoid_crowds: bool = False