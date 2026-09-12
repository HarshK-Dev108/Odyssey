import logging
import re
from typing import Optional, List, Dict, Tuple
from motor.motor_asyncio import AsyncIOMotorDatabase
from sqlalchemy.orm import Session

from app.models.trip import Trip
from app.models.itinerary import Itinerary, ItineraryItem
from app.schemas.generator import (
    BudgetBreakdown,
    BudgetSummary,
    WeatherSummary,
    ItineraryGenerationResponse,
)
from app.schemas.itinerary import ItineraryResponse
from app.services.itinerary_service import get_or_create_itinerary
from app.services.weather_service import get_weather_forecast

logger = logging.getLogger(__name__)

CITY_CODE_MAP = {
    "delhi": ["DEL", "DELHI", "New Delhi"],
    "new delhi": ["DEL", "DELHI", "New Delhi"],
    "mumbai": ["BOM", "MUMBAI", "Bombay"],
    "goa": ["GOA", "GOI", "GOX", "Goa"],
    "jaipur": ["JAI", "JAIPUR", "Jaipur"],
    "amritsar": ["ATQ", "AMRITSAR", "Amritsar"],
    "varanasi": ["VNS", "VARANASI", "Varanasi"],
    "udaipur": ["UDR", "UDAIPUR", "Udaipur"],
    "kochi": ["COK", "KOCHI", "Cochin"],
    "bengaluru": ["BLR", "BENGALURU", "Bangalore"],
    "bangalore": ["BLR", "BENGALURU", "Bangalore"],
    "manali": ["KUU", "MANALI", "Kullu", "Manali"],
    "shillong": ["SHL", "SHILLONG", "Shillong"],
    "rishikesh": ["DED", "RISHIKESH", "Dehradun", "Rishikesh"],
}


def _get_city_search_patterns(city_name: str) -> List[str]:
    """Return regex patterns and airport code aliases for a given city name."""
    clean = city_name.strip()
    key = clean.lower()
    aliases = CITY_CODE_MAP.get(key, [clean])
    if clean not in aliases:
        aliases.append(clean)
    return aliases


async def _fetch_destination_document(
    destination: str,
    mongo_db: AsyncIOMotorDatabase
) -> Optional[dict]:
    """Find destination document by name in MongoDB."""
    return await mongo_db["destinations"].find_one({
        "name": {"$regex": f"^{re.escape(destination.strip())}$", "$options": "i"}
    })


async def _fetch_matching_hotels(
    destination: str,
    dest_id: Optional[str],
    mongo_db: AsyncIOMotorDatabase
) -> List[dict]:
    """Fetch all hotels belonging to destination id or destination name."""
    queries = [{"destination_id": {"$regex": f"^{re.escape(destination.strip())}$", "$options": "i"}}]
    if dest_id:
        queries.append({"destination_id": dest_id})

    return await mongo_db["hotels"].find({"$or": queries}).to_list(length=100)


async def _fetch_matching_activities(
    destination: str,
    dest_id: Optional[str],
    mongo_db: AsyncIOMotorDatabase
) -> List[dict]:
    """Fetch all activities belonging to destination id or destination name."""
    queries = [{"destination_id": {"$regex": f"^{re.escape(destination.strip())}$", "$options": "i"}}]
    if dest_id:
        queries.append({"destination_id": dest_id})

    return await mongo_db["activities"].find({"$or": queries}).to_list(length=100)


async def _fetch_matching_flights(
    from_city: str,
    destination: str,
    mongo_db: AsyncIOMotorDatabase
) -> Tuple[List[dict], List[dict]]:
    """Fetch outbound and return flights matching origin and destination city aliases."""
    origin_aliases = _get_city_search_patterns(from_city)
    dest_aliases = _get_city_search_patterns(destination)

    origin_pattern = re.compile(f"^({'|'.join(re.escape(a) for a in origin_aliases)})$", re.I)
    dest_pattern = re.compile(f"^({'|'.join(re.escape(a) for a in dest_aliases)})$", re.I)

    outbound_query = {
        "origin": origin_pattern,
        "destination": dest_pattern,
    }
    return_query = {
        "origin": dest_pattern,
        "destination": origin_pattern,
    }

    outbound = await mongo_db["flights"].find(outbound_query).to_list(length=50)
    returning = await mongo_db["flights"].find(return_query).to_list(length=50)
    return outbound, returning


def score_hotel(
    hotel: dict,
    trip: Trip,
    nights: int,
    hotel_budget_target: float
) -> float:
    """Multi-criteria scoring function for hotel feasibility and preference."""
    total_price = float(hotel.get("price_per_night", 0.0)) * nights
    rating = float(hotel.get("rating", 3.0))
    preferred_rating = float(trip.hotel_rating or 3)

    # 1. Rating preference (0 to 35 pts)
    if rating >= preferred_rating:
        rating_score = 30.0 + min(5.0, (rating - preferred_rating) * 5.0)
    else:
        # Significantly penalize hotels below user's star expectation
        rating_score = max(0.0, 30.0 - (preferred_rating - rating) * 20.0)

    # 2. Budget compatibility (0 to 35 pts)
    if total_price <= hotel_budget_target:
        budget_score = 35.0
    elif total_price <= trip.budget:
        overage_ratio = (total_price - hotel_budget_target) / max(trip.budget - hotel_budget_target, 1.0)
        budget_score = max(5.0, 35.0 - (30.0 * overage_ratio))
    else:
        budget_score = 0.0

    # 3. Overall quality (0 to 20 pts)
    quality_score = (rating / 5.0) * 20.0

    # 4. Crowd preference (0 to 10 pts)
    crowd_score = 5.0
    if trip.avoid_crowds:
        rooms = int(hotel.get("available_rooms", 10))
        if rooms < 15:
            crowd_score = 10.0

    return rating_score + budget_score + quality_score + crowd_score


def score_flight(
    flight: dict,
    trip: Trip,
    direction: str,
    flight_budget_target: float
) -> float:
    """Multi-criteria scoring function for flight route, price, and schedule."""
    travellers = max(1, trip.travellers or 1)
    total_price = float(flight.get("price", 0.0)) * travellers
    stops = int(flight.get("stops", 0))

    # 1. Price / Budget (0 to 45 pts)
    if total_price <= flight_budget_target:
        price_score = 45.0 - (15.0 * (total_price / max(flight_budget_target, 1.0)))
    elif total_price <= trip.budget:
        overage = (total_price - flight_budget_target) / max(trip.budget, 1.0)
        price_score = max(5.0, 30.0 - (25.0 * overage))
    else:
        price_score = 0.0

    # 2. Timing preference (0 to 35 pts)
    timing_score = 20.0
    dep_time = flight.get("departure_time")
    if dep_time:
        try:
            if isinstance(dep_time, str):
                hour = int(dep_time.split("T")[1].split(":")[0])
            elif hasattr(dep_time, "hour"):
                hour = dep_time.hour
            else:
                hour = 10

            if direction == "outbound":
                if 7 <= hour <= 12:
                    timing_score = 35.0
                elif 12 < hour <= 16:
                    timing_score = 25.0
                else:
                    timing_score = 15.0
            else:
                if 14 <= hour <= 21:
                    timing_score = 35.0
                elif 11 <= hour < 14:
                    timing_score = 25.0
                else:
                    timing_score = 15.0
        except Exception:
            pass

    # 3. Non-stop convenience (0 to 20 pts)
    stops_score = 20.0 if stops == 0 else max(0.0, 20.0 - (stops * 10.0))

    return price_score + timing_score + stops_score


def score_activity(
    act: dict,
    trip: Trip,
    is_rainy: bool,
    travellers: int,
    activity_budget_target: float
) -> float:
    """Multi-criteria scoring function for activities matching interests, rating, value and weather."""
    category = (act.get("category") or "").strip().lower()
    name = (act.get("name") or "").strip().lower()
    desc = (act.get("description") or "").strip().lower()
    rating = float(act.get("rating", 4.0))
    price = float(act.get("price", 0.0)) * travellers

    # 1. Interest Matching (0 to 45 pts)
    trip_interests = [i.strip().lower() for i in (trip.interests or []) if i.strip()]
    interest_score = 20.0  # baseline
    if trip_interests:
        matches = 0
        for interest in trip_interests:
            if interest in category or interest in name or interest in desc:
                matches += 1
            if interest in ["beach", "sea"] and any(k in category or k in name for k in ["beach", "water", "island", "snorkeling", "scuba"]):
                matches += 1
            if interest in ["food", "culinary", "dining"] and any(k in category or k in name for k in ["food", "culinary", "trail", "cooking"]):
                matches += 1
            if interest in ["adventure", "trekking"] and any(k in category or k in name for k in ["adventure", "trek", "rafting", "safari", "scuba", "paragliding"]):
                matches += 1
            if interest in ["culture", "heritage", "history"] and any(k in category or k in name for k in ["culture", "heritage", "fort", "palace", "temple", "museum"]):
                matches += 1
            if interest in ["wellness", "yoga", "spiritual"] and any(k in category or k in name for k in ["wellness", "yoga", "spiritual", "aarti"]):
                matches += 1

        if matches > 0:
            interest_score = min(45.0, 25.0 + (matches * 10.0))
        else:
            interest_score = 5.0

    # 2. Rating Score (0 to 25 pts)
    rating_score = rating * 5.0

    # 3. Price & Value (0 to 20 pts)
    if price <= activity_budget_target:
        value_score = 20.0 - (5.0 * (price / max(activity_budget_target, 1.0)))
    else:
        value_score = max(0.0, 15.0 - (15.0 * (price - activity_budget_target) / max(activity_budget_target, 1.0)))

    # 4. Weather Adaptation (-15 to +15 pts)
    weather_score = 0.0
    indoor_keywords = ["food", "heritage", "culture", "wellness", "museum", "shopping", "culinary", "spiritual", "cooking"]
    outdoor_keywords = ["adventure", "water sports", "nature", "trekking", "beach", "safari", "hiking", "paragliding", "scuba"]
    is_indoor = any(k in category or k in name for k in indoor_keywords)
    is_outdoor = any(k in category or k in name for k in outdoor_keywords)

    if is_rainy:
        if is_indoor:
            weather_score = 15.0
        elif is_outdoor:
            weather_score = -15.0

    return interest_score + rating_score + value_score + weather_score


async def generate_intelligent_itinerary(
    trip: Trip,
    db: Session,
    mongo_db: AsyncIOMotorDatabase,
) -> ItineraryGenerationResponse:
    """
    Deterministically plan, score, and persist a complete trip itinerary
    from MongoDB catalogue data, taking into account trip constraints,
    pace, budget, and live weather.
    """
    warnings: List[str] = []
    nights = max(1, (trip.end_date - trip.start_date).days)
    travellers = max(1, trip.travellers or 1)
    total_budget = float(trip.budget or 0.0)

    # 1. Budget Targets
    hotel_budget_target = total_budget * 0.40
    flights_budget_target = total_budget * 0.30
    single_flight_target = flights_budget_target / 2.0
    activity_budget_target = total_budget * 0.20

    # 2. Destination Document & Weather
    dest_doc = await _fetch_destination_document(trip.destination, mongo_db)
    dest_id = str(dest_doc["_id"]) if dest_doc else None

    weather_summary = WeatherSummary(available=False)
    is_rainy = False
    if dest_doc and dest_doc.get("latitude") is not None and dest_doc.get("longitude") is not None:
        try:
            forecast = await get_weather_forecast(
                latitude=float(dest_doc["latitude"]),
                longitude=float(dest_doc["longitude"])
            )
            is_rainy = (
                (forecast.weather_code is not None and forecast.weather_code >= 51)
                or ("rain" in (forecast.condition or "").lower())
                or ("drizzle" in (forecast.condition or "").lower())
                or ("storm" in (forecast.condition or "").lower())
            )
            weather_summary = WeatherSummary(
                available=True,
                condition=forecast.condition,
                temperature=forecast.temperature,
                is_rainy=is_rainy,
                rain_safe_prioritized=is_rainy,
            )
            if is_rainy:
                warnings.append(
                    f"Rain or adverse weather detected ({forecast.condition}); "
                    "prioritized indoor and rain-safe activities."
                )
        except Exception as exc:
            logger.info(f"Live weather lookup gracefully bypassed: {exc}")

    # 3. Hotel Selection
    hotels = await _fetch_matching_hotels(trip.destination, dest_id, mongo_db)
    selected_hotel_id: Optional[str] = None
    hotel_cost = 0.0

    if hotels:
        scored_hotels = sorted(
            hotels,
            key=lambda h: score_hotel(h, trip, nights, hotel_budget_target),
            reverse=True
        )
        best_hotel = scored_hotels[0]
        selected_hotel_id = str(best_hotel["_id"])
        hotel_cost = float(best_hotel.get("price_per_night", 0.0)) * nights
    else:
        warnings.append(f"No hotels found matching destination '{trip.destination}' in catalogue.")

    # 4. Flight Selection
    outbound_flights, return_flights = await _fetch_matching_flights(
        trip.from_city,
        trip.destination,
        mongo_db
    )
    outbound_flight_id: Optional[str] = None
    return_flight_id: Optional[str] = None
    flights_cost = 0.0

    if outbound_flights:
        scored_outbound = sorted(
            outbound_flights,
            key=lambda f: score_flight(f, trip, "outbound", single_flight_target),
            reverse=True
        )
        best_outbound = scored_outbound[0]
        outbound_flight_id = str(best_outbound["_id"])
        flights_cost += float(best_outbound.get("price", 0.0)) * travellers
    else:
        warnings.append(f"No outbound flights found matching route '{trip.from_city}' to '{trip.destination}' in catalogue.")

    if return_flights:
        scored_return = sorted(
            return_flights,
            key=lambda f: score_flight(f, trip, "return", single_flight_target),
            reverse=True
        )
        best_return = scored_return[0]
        return_flight_id = str(best_return["_id"])
        flights_cost += float(best_return.get("price", 0.0)) * travellers
    else:
        warnings.append(f"No return flights found matching route '{trip.destination}' to '{trip.from_city}' in catalogue.")

    # 5. Activity Selection & Pace Scheduling
    activities = await _fetch_matching_activities(trip.destination, dest_id, mongo_db)
    planned_items: List[dict] = []
    activities_cost = 0.0

    pace_key = (trip.pace or "moderate").strip().lower()
    if pace_key == "relaxed":
        slots_per_day = [("morning", "09:30")]
    elif pace_key == "active":
        slots_per_day = [("morning", "09:30"), ("afternoon", "14:30"), ("evening", "18:30")]
    else:
        # moderate
        slots_per_day = [("morning", "09:30"), ("afternoon", "14:30")]

    if activities:
        scored_activities = sorted(
            activities,
            key=lambda a: score_activity(a, trip, is_rainy, travellers, activity_budget_target),
            reverse=True
        )

        act_index = 0
        total_acts = len(scored_activities)

        for day in range(1, nights + 1):
            for slot_name, slot_time in slots_per_day:
                if act_index < total_acts:
                    act = scored_activities[act_index]
                    cost = float(act.get("price", 0.0)) * travellers
                    planned_items.append({
                        "day_number": day,
                        "time_slot": slot_name,
                        "activity_id": str(act["_id"]),
                        "title_override": act.get("name"),
                        "start_time": slot_time,
                        "duration_minutes": act.get("duration_minutes", 120),
                        "estimated_cost": cost,
                    })
                    activities_cost += cost
                    act_index += 1
                elif total_acts > 0 and pace_key == "active":
                    # Reuse top activity for high density if requested
                    act = scored_activities[act_index % total_acts]
                    cost = float(act.get("price", 0.0)) * travellers
                    planned_items.append({
                        "day_number": day,
                        "time_slot": slot_name,
                        "activity_id": str(act["_id"]),
                        "title_override": act.get("name"),
                        "start_time": slot_time,
                        "duration_minutes": act.get("duration_minutes", 120),
                        "estimated_cost": cost,
                    })
                    activities_cost += cost
                    act_index += 1
    else:
        warnings.append(f"No activities found matching destination '{trip.destination}' in catalogue.")

    # 6. Total Cost & Budget Analysis
    estimated_total = round(hotel_cost + flights_cost + activities_cost, 2)
    is_over = estimated_total > total_budget
    over_amount = round(max(0.0, estimated_total - total_budget), 2)
    rem_budget = round(max(0.0, total_budget - estimated_total), 2)

    if is_over:
        warnings.append(
            f"Estimated total cost (₹{estimated_total:,.2f}) exceeds trip budget "
            f"(₹{total_budget:,.2f}) by ₹{over_amount:,.2f}."
        )

    # 7. Relational Persistence
    itinerary = get_or_create_itinerary(trip, db)
    itinerary.selected_hotel_id = selected_hotel_id
    itinerary.outbound_flight_id = outbound_flight_id
    itinerary.return_flight_id = return_flight_id
    itinerary.estimated_total_cost = estimated_total

    # Replace existing items with newly planned schedule
    for old_item in list(itinerary.items):
        db.delete(old_item)
    db.flush()

    for item_data in planned_items:
        new_item = ItineraryItem(
            itinerary_id=itinerary.id,
            day_number=item_data["day_number"],
            time_slot=item_data["time_slot"],
            activity_id=item_data["activity_id"],
            title_override=item_data["title_override"],
            start_time=item_data["start_time"],
            duration_minutes=item_data["duration_minutes"],
            estimated_cost=item_data["estimated_cost"],
        )
        db.add(new_item)

    db.commit()
    db.refresh(itinerary)

    budget_summary = BudgetSummary(
        total_budget=total_budget,
        estimated_total_cost=estimated_total,
        remaining_budget=rem_budget,
        over_budget_amount=over_amount,
        is_over_budget=is_over,
        breakdown=BudgetBreakdown(
            hotel_cost=round(hotel_cost, 2),
            flights_cost=round(flights_cost, 2),
            activities_cost=round(activities_cost, 2),
        )
    )

    return ItineraryGenerationResponse(
        message="Itinerary generated successfully",
        trip_id=trip.id,
        itinerary=ItineraryResponse.model_validate(itinerary),
        budget_summary=budget_summary,
        weather_summary=weather_summary,
        warnings=warnings,
    )
