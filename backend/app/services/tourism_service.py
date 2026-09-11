import logging
import re
from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.data.travel_data import get_travel_options


logger = logging.getLogger(__name__)


def _copy_crowd_fields(option: dict, document: dict) -> dict:
    for field in ("crowd_level", "crowd_score", "crowd_data"):
        if field in document:
            option[field] = document[field]
    return option


def _positive_number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None

    try:
        number = float(value)
    except (TypeError, ValueError):
        return None

    return number if number >= 0 else None


def _case_insensitive_exact(value: str) -> dict:
    return {"$regex": f"^{re.escape(value.strip())}$", "$options": "i"}


def _normalize_hotel(document: dict, nights: int) -> dict | None:
    nightly_price = _positive_number(document.get("price_per_night"))
    name = document.get("name")

    if nightly_price is None or not isinstance(name, str) or not name.strip():
        return None

    total_price = nightly_price * nights
    return _copy_crowd_fields({
        "name": name,
        "type": "hotel",
        "price": total_price,
        "unit_price": nightly_price,
        "price_unit": "per_night",
        "rating": document.get("rating", 0),
        "interests": ["hotel", "stay"],
        "currency": document.get("currency", "INR"),
        "nights": nights,
        "source": "mongodb",
        "source_id": str(document.get("_id")) if document.get("_id") else None,
        "destination_id": document.get("destination_id"),
        "amenities": document.get("amenities", []),
    }, document)


def _normalize_activity(document: dict, travellers: int) -> dict | None:
    unit_price = _positive_number(document.get("price"))
    name = document.get("name")

    if unit_price is None or not isinstance(name, str) or not name.strip():
        return None

    category = document.get("category", "Sightseeing")
    total_price = unit_price * travellers
    return _copy_crowd_fields({
        "name": name,
        "type": "activity",
        "price": total_price,
        "unit_price": unit_price,
        "price_unit": "per_person",
        "travellers": travellers,
        "rating": document.get("rating", 0),
        "interests": [str(category).lower()],
        "category": category,
        "currency": document.get("currency", "INR"),
        "duration_minutes": document.get("duration_minutes"),
        "location": document.get("location"),
        "source": "mongodb",
        "source_id": str(document.get("_id")) if document.get("_id") else None,
        "destination_id": document.get("destination_id"),
    }, document)


def _normalize_flight(document: dict, travellers: int) -> dict | None:
    unit_price = _positive_number(document.get("price"))
    name = document.get("flight_number") or document.get("airline")

    if unit_price is None or not isinstance(name, str) or not name.strip():
        return None

    return _copy_crowd_fields({
        "name": name,
        "type": "flight",
        "price": unit_price * travellers,
        "unit_price": unit_price,
        "price_unit": "per_person",
        "travellers": travellers,
        "rating": 0,
        "interests": ["flight", "transport"],
        "currency": document.get("currency", "INR"),
        "origin": document.get("origin"),
        "destination": document.get("destination"),
        "airline": document.get("airline"),
        "stops": document.get("stops", 0),
        "source": "mongodb",
        "source_id": str(document.get("_id")) if document.get("_id") else None,
    }, document)


async def get_tourism_options(
    db: AsyncIOMotorDatabase,
    destination: str,
    from_city: str,
    nights: int,
    travellers: int,
) -> list[dict]:
    """Return MongoDB tourism options normalized for the existing AI pipeline.

    Static travel data remains the fallback when MongoDB is unavailable or does
    not contain any valid options for the requested trip.
    """
    fallback = get_travel_options(destination)
    safe_nights = max(nights, 1)
    safe_travellers = max(travellers, 1)

    try:
        destination_document = await db["destinations"].find_one(
            {"name": _case_insensitive_exact(destination)}
        )

        if not destination_document:
            return fallback

        destination_id = str(destination_document.get("_id"))
        hotels = await db["hotels"].find(
            {"destination_id": destination_id}
        ).to_list(length=100)
        activities = await db["activities"].find(
            {"destination_id": destination_id}
        ).to_list(length=100)

        flights = await db["flights"].find({
            "origin": _case_insensitive_exact(from_city),
            "destination": _case_insensitive_exact(destination),
        }).to_list(length=100)

        options = [
            normalized
            for document in hotels
            for normalized in [_normalize_hotel(document, safe_nights)]
            if normalized is not None
        ]
        options.extend(
            normalized
            for document in activities
            for normalized in [_normalize_activity(document, safe_travellers)]
            if normalized is not None
        )
        options.extend(
            normalized
            for document in flights
            for normalized in [_normalize_flight(document, safe_travellers)]
            if normalized is not None
        )

        return options or fallback
    except Exception:
        logger.exception(
            "MongoDB tourism lookup failed for destination '%s'; using fallback",
            destination,
        )
        return fallback