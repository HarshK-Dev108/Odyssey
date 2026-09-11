import pytest
from pydantic import ValidationError

from app.schemas.trip import TripRequest


def valid_trip(**overrides):
    value = {
        "from_city": "Delhi",
        "destination": "Goa",
        "start_date": "2026-05-01",
        "end_date": "2026-05-05",
        "travellers": 2,
        "budget": 25000,
    }
    value.update(overrides)
    return value


def test_trip_rejects_invalid_date_order():
    with pytest.raises(ValidationError, match="end_date"):
        TripRequest(**valid_trip(start_date="2026-05-05", end_date="2026-05-01"))


def test_trip_rejects_invalid_pace_and_accepts_normalized_pace():
    with pytest.raises(ValidationError, match="pace"):
        TripRequest(**valid_trip(pace="sprint"))
    assert TripRequest(**valid_trip(pace=" ACTIVE ")).pace == "active"


def test_trip_validates_currency_and_budget():
    with pytest.raises(ValidationError, match="currency"):
        TripRequest(**valid_trip(currency="rupees"))
    with pytest.raises(ValidationError, match="budget"):
        TripRequest(**valid_trip(budget=0))