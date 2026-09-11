from datetime import date

from pydantic import BaseModel, Field, field_validator, model_validator


class TripRequest(BaseModel):
    from_city: str = Field(..., min_length=2)
    destination: str = Field(..., min_length=2)

    start_date: date
    end_date: date

    travellers: int = Field(..., ge=1)
    budget: float = Field(..., gt=0)

    currency: str = "INR"

    interests: list[str] = Field(default_factory=list)

    hotel_rating: int = Field(default=3, ge=1, le=5)
    pace: str = "moderate"
    avoid_crowds: bool = False

    @field_validator("pace")
    @classmethod
    def validate_pace(cls, value: str) -> str:
        normalized = value.strip().casefold()
        if normalized not in {"relaxed", "moderate", "active"}:
            raise ValueError("pace must be relaxed, moderate, or active")
        return normalized

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, value: str) -> str:
        normalized = value.strip().upper()
        if len(normalized) != 3 or not normalized.isalpha():
            raise ValueError("currency must be a three-letter code")
        return normalized

    @model_validator(mode="after")
    def validate_dates(self):
        if self.end_date <= self.start_date:
            raise ValueError("end_date must be after start_date")
        return self