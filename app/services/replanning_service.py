import logging
import re
from typing import Optional, List, Tuple
from motor.motor_asyncio import AsyncIOMotorDatabase
from sqlalchemy.orm import Session
from pydantic import ValidationError

from app.models.trip import Trip
from app.models.itinerary import Itinerary, ItineraryItem
from app.schemas.ai_chat import (
    SupportedIntent,
    AIActionParameters,
    AIStructuredAction,
    BudgetComparison,
    AIChatResponse,
)
from app.schemas.itinerary import ItineraryResponse
from app.services.itinerary_service import (
    get_or_create_itinerary,
    recalculate_itinerary_cost,
)
from app.services.itinerary_generator_service import (
    _fetch_destination_document,
    _fetch_matching_hotels,
    _fetch_matching_activities,
    _fetch_matching_flights,
)

RAIN_SAFE_CATEGORIES = ["food", "heritage", "culture", "wellness", "museum", "shopping", "culinary", "spiritual", "cooking"]
RAIN_UNFRIENDLY_CATEGORIES = ["adventure", "water sports", "nature", "trekking", "beach", "safari", "hiking", "paragliding", "scuba"]
from app.ai.llm.provider import LLMProvider

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are YatraAI, an intelligent travel assistant for the Odyssey travel planner.
Your job is to interpret the user's message regarding their trip itinerary and output a strictly valid JSON object with the desired action.

Supported intents:
- make_trip_cheaper: User wants to reduce total cost or save money. Extract "target_savings" if specified as a number.
- change_hotel: User wants to change, swap, or upgrade/downgrade hotel, or chose a specific hotel name. Extract "hotel_name" and/or "hotel_rating".
- add_activity: User wants to add an activity. Extract "activity_name", "category", "day_number", or "time_slot".
- remove_activity: User wants to remove or cancel an activity. Extract "activity_name", "day_number", or "item_id".
- replace_activity: User wants to replace one activity with another. Extract "current_activity_name" and "new_activity_name".
- more_adventure: User wants more adventure, adrenaline, thrill, or water sports.
- more_relaxed: User wants a slower pace, more relaxation, fewer activities, or free time.
- weather_safe_plan: User asks for weather-safe, indoor, or rain-friendly alternatives.
- explain_itinerary: User asks why recommendations were made, or asks for an explanation/overview of the itinerary.
- unknown: Any message that is off-topic, chit-chat, unsupported, or cannot be mapped to the above intents.

Response JSON Schema:
{
  "intent": "<one of the supported intents above>",
  "parameters": {
    "target_savings": <number or null>,
    "hotel_name": <string or null>,
    "hotel_rating": <number or null>,
    "activity_name": <string or null>,
    "current_activity_name": <string or null>,
    "new_activity_name": <string or null>,
    "category": <string or null>,
    "day_number": <integer or null>,
    "time_slot": <string or null>,
    "item_id": <integer or null>
  },
  "reasoning": "<brief explanation of the parsed intent>"
}

Do NOT output markdown, backticks, or any text other than the pure JSON object."""


async def replan_cheaper_trip(
    trip: Trip,
    itinerary: Itinerary,
    params: AIActionParameters,
    mongo_db: AsyncIOMotorDatabase,
    db: Session,
) -> Tuple[List[str], str]:
    """
    Controlled replanning function to find cheaper hotel, flights, and activities in MongoDB catalogue.
    """
    changes_made = []
    nights = max(1, (trip.end_date - trip.start_date).days)
    travellers = max(1, trip.travellers or 1)

    dest_doc = await _fetch_destination_document(trip.destination, mongo_db)
    dest_id = str(dest_doc["_id"]) if dest_doc else None

    # 1. Cheaper Hotel
    if itinerary.selected_hotel_id:
        from bson import ObjectId
        current_hotel = None
        try:
            current_hotel = await mongo_db["hotels"].find_one({"_id": ObjectId(itinerary.selected_hotel_id)})
        except Exception:
            pass

        if current_hotel:
            current_price = float(current_hotel.get("price_per_night", 0.0))
            all_hotels = await _fetch_matching_hotels(trip.destination, dest_id, mongo_db)
            # Find hotels with lower price
            cheaper_hotels = [h for h in all_hotels if float(h.get("price_per_night", 0.0)) < current_price]
            if cheaper_hotels:
                # Pick the highest rated among cheaper hotels
                cheaper_hotels.sort(key=lambda h: (float(h.get("rating", 0.0)), -float(h.get("price_per_night", 0.0))), reverse=True)
                best_cheaper = cheaper_hotels[0]
                saved_hotel = (current_price - float(best_cheaper.get("price_per_night", 0.0))) * nights
                itinerary.selected_hotel_id = str(best_cheaper["_id"])
                changes_made.append(
                    f"Swapped hotel to '{best_cheaper.get('name')}' (₹{best_cheaper.get('price_per_night')}/night, saving ₹{saved_hotel:,.2f})"
                )

    # 2. Cheaper Flights
    outbound_flights, return_flights = await _fetch_matching_flights(trip.from_city or "Delhi", trip.destination, mongo_db)
    if itinerary.outbound_flight_id and outbound_flights:
        from bson import ObjectId
        current_outbound = None
        try:
            current_outbound = await mongo_db["flights"].find_one({"_id": ObjectId(itinerary.outbound_flight_id)})
        except Exception:
            pass
        if current_outbound:
            cur_price = float(current_outbound.get("price", 0.0))
            cheaper_out = [f for f in outbound_flights if float(f.get("price", 0.0)) < cur_price]
            if cheaper_out:
                cheaper_out.sort(key=lambda f: float(f.get("price", 0.0)))
                itinerary.outbound_flight_id = str(cheaper_out[0]["_id"])
                saved_flight = (cur_price - float(cheaper_out[0].get("price", 0.0))) * travellers
                changes_made.append(f"Swapped outbound flight to cheaper option (saving ₹{saved_flight:,.2f})")

    if itinerary.return_flight_id and return_flights:
        from bson import ObjectId
        current_return = None
        try:
            current_return = await mongo_db["flights"].find_one({"_id": ObjectId(itinerary.return_flight_id)})
        except Exception:
            pass
        if current_return:
            cur_price = float(current_return.get("price", 0.0))
            cheaper_ret = [f for f in return_flights if float(f.get("price", 0.0)) < cur_price]
            if cheaper_ret:
                cheaper_ret.sort(key=lambda f: float(f.get("price", 0.0)))
                itinerary.return_flight_id = str(cheaper_ret[0]["_id"])
                saved_flight = (cur_price - float(cheaper_ret[0].get("price", 0.0))) * travellers
                changes_made.append(f"Swapped return flight to cheaper option (saving ₹{saved_flight:,.2f})")

    # 3. Cheaper Activities
    scheduled_items = db.query(ItineraryItem).filter(ItineraryItem.itinerary_id == itinerary.id).all()
    if scheduled_items:
        all_activities = await _fetch_matching_activities(trip.destination, dest_id, mongo_db)
        scheduled_activity_ids = {item.activity_id for item in scheduled_items if item.activity_id}

        for item in scheduled_items:
            item_cost = float(item.estimated_cost or 0.0) / travellers
            # Find cheaper activity in same destination
            cheaper_acts = [
                a for a in all_activities
                if str(a["_id"]) not in scheduled_activity_ids and float(a.get("price", 0.0)) < item_cost
            ]
            if cheaper_acts:
                cheaper_acts.sort(key=lambda a: (float(a.get("rating", 0.0)), -float(a.get("price", 0.0))), reverse=True)
                picked = cheaper_acts[0]
                old_title = item.title_override or "Activity"
                saved_act = (item_cost - float(picked.get("price", 0.0))) * travellers
                item.activity_id = str(picked["_id"])
                item.title_override = picked.get("name")
                item.estimated_cost = float(picked.get("price", 0.0)) * travellers
                scheduled_activity_ids.add(str(picked["_id"]))
                changes_made.append(f"Replaced '{old_title}' with '{picked.get('name')}' on Day {item.day_number} (saving ₹{saved_act:,.2f})")
                break

    if not changes_made:
        return [], "Your itinerary is already using the most affordable options available in the catalogue for this destination."

    return changes_made, f"Successfully optimized your itinerary with {len(changes_made)} cost-saving update(s)."


async def replan_hotel(
    trip: Trip,
    itinerary: Itinerary,
    params: AIActionParameters,
    mongo_db: AsyncIOMotorDatabase,
    db: Session,
) -> Tuple[List[str], str]:
    """Controlled hotel change or swap from MongoDB catalogue."""
    dest_doc = await _fetch_destination_document(trip.destination, mongo_db)
    dest_id = str(dest_doc["_id"]) if dest_doc else None
    all_hotels = await _fetch_matching_hotels(trip.destination, dest_id, mongo_db)

    if not all_hotels:
        return [], f"No hotels found in the catalogue for {trip.destination}."

    chosen_hotel = None
    if params.hotel_name:
        # Search by name
        pat = re.compile(re.escape(params.hotel_name.strip()), re.I)
        for h in all_hotels:
            if pat.search(h.get("name", "")):
                chosen_hotel = h
                break
        if not chosen_hotel:
            # Try searching across whole collection if destination had slight mismatch
            chosen_hotel = await mongo_db["hotels"].find_one({"name": pat})

        if not chosen_hotel:
            return [], f"Hotel '{params.hotel_name}' was not found in the catalogue."
    elif params.hotel_rating:
        # Filter by rating preference
        rated_hotels = [h for h in all_hotels if float(h.get("rating", 0.0)) >= params.hotel_rating]
        if rated_hotels:
            rated_hotels.sort(key=lambda h: float(h.get("rating", 0.0)), reverse=True)
            chosen_hotel = rated_hotels[0]
        else:
            chosen_hotel = max(all_hotels, key=lambda h: float(h.get("rating", 0.0)))
    else:
        # Upgrade or swap: pick highest rated hotel different from current
        curr_id = itinerary.selected_hotel_id
        candidates = [h for h in all_hotels if str(h["_id"]) != curr_id]
        if candidates:
            candidates.sort(key=lambda h: float(h.get("rating", 0.0)), reverse=True)
            chosen_hotel = candidates[0]
        elif all_hotels:
            chosen_hotel = all_hotels[0]

    if chosen_hotel:
        if str(chosen_hotel["_id"]) == itinerary.selected_hotel_id:
            return [], f"'{chosen_hotel.get('name')}' is already your selected hotel."

        itinerary.selected_hotel_id = str(chosen_hotel["_id"])
        change = f"Swapped hotel to '{chosen_hotel.get('name')}' (Rating: {chosen_hotel.get('rating', 'N/A')}★, ₹{chosen_hotel.get('price_per_night', 0)}/night)"
        return [change], f"Updated your hotel selection to '{chosen_hotel.get('name')}'."

    return [], "No suitable hotel alternative could be found in the catalogue."


async def replan_add_activity(
    trip: Trip,
    itinerary: Itinerary,
    params: AIActionParameters,
    mongo_db: AsyncIOMotorDatabase,
    db: Session,
) -> Tuple[List[str], str]:
    """Controlled activity addition from MongoDB catalogue."""
    dest_doc = await _fetch_destination_document(trip.destination, mongo_db)
    dest_id = str(dest_doc["_id"]) if dest_doc else None
    all_acts = await _fetch_matching_activities(trip.destination, dest_id, mongo_db)

    if not all_acts:
        return [], f"No activities found in the catalogue for {trip.destination}."

    scheduled_items = db.query(ItineraryItem).filter(ItineraryItem.itinerary_id == itinerary.id).all()
    scheduled_ids = {item.activity_id for item in scheduled_items if item.activity_id}

    target_act = None
    if params.activity_name:
        pat = re.compile(re.escape(params.activity_name.strip()), re.I)
        for a in all_acts:
            if pat.search(a.get("name", "")):
                target_act = a
                break
        if not target_act:
            # Fallback across collection
            target_act = await mongo_db["activities"].find_one({"name": pat})
        if not target_act:
            return [], f"Activity '{params.activity_name}' was not found in the catalogue."
    elif params.category:
        cat_pat = re.compile(re.escape(params.category.strip()), re.I)
        matching_cats = [a for a in all_acts if cat_pat.search(a.get("category", "")) and str(a["_id"]) not in scheduled_ids]
        if matching_cats:
            matching_cats.sort(key=lambda a: float(a.get("rating", 0.0)), reverse=True)
            target_act = matching_cats[0]
    else:
        candidates = [a for a in all_acts if str(a["_id"]) not in scheduled_ids]
        if candidates:
            candidates.sort(key=lambda a: float(a.get("rating", 0.0)), reverse=True)
            target_act = candidates[0]

    if not target_act:
        return [], "No suitable new activity found in the catalogue."

    if str(target_act["_id"]) in scheduled_ids:
        return [], f"Activity '{target_act.get('name')}' is already scheduled in your itinerary."

    # Determine day number
    total_days = max(1, (trip.end_date - trip.start_date).days)
    target_day = params.day_number if (params.day_number and 1 <= params.day_number <= total_days) else None
    if not target_day:
        # Find day with fewest activities
        day_counts = {d: 0 for d in range(1, total_days + 1)}
        for item in scheduled_items:
            if item.day_number in day_counts:
                day_counts[item.day_number] += 1
        target_day = min(day_counts, key=day_counts.get)

    # Determine slot
    day_items = [item for item in scheduled_items if item.day_number == target_day]
    used_slots = {item.time_slot for item in day_items}
    slot = params.time_slot if params.time_slot in {"morning", "afternoon", "evening"} else None
    if not slot:
        for s in ["morning", "afternoon", "evening"]:
            if s not in used_slots:
                slot = s
                break
        if not slot:
            slot = "afternoon"

    slot_times = {"morning": "09:30", "afternoon": "14:00", "evening": "18:00"}
    travellers = max(1, trip.travellers or 1)
    new_item = ItineraryItem(
        itinerary_id=itinerary.id,
        day_number=target_day,
        time_slot=slot,
        activity_id=str(target_act["_id"]),
        title_override=target_act.get("name"),
        start_time=slot_times.get(slot, "14:00"),
        duration_minutes=int(target_act.get("duration_hours", 2) * 60),
        estimated_cost=float(target_act.get("price", 0.0)) * travellers,
    )
    db.add(new_item)
    change = f"Added '{target_act.get('name')}' to Day {target_day} ({slot} slot, ₹{new_item.estimated_cost:,.2f})"
    return [change], f"Added '{target_act.get('name')}' to your itinerary on Day {target_day}."


async def replan_remove_activity(
    trip: Trip,
    itinerary: Itinerary,
    params: AIActionParameters,
    mongo_db: AsyncIOMotorDatabase,
    db: Session,
) -> Tuple[List[str], str]:
    """Controlled activity removal from itinerary items."""
    scheduled_items = db.query(ItineraryItem).filter(ItineraryItem.itinerary_id == itinerary.id).all()
    if not scheduled_items:
        return [], "There are no activities in your itinerary to remove."

    target_item = None
    if params.item_id:
        for item in scheduled_items:
            if item.id == params.item_id:
                target_item = item
                break
    elif params.activity_name:
        pat = re.compile(re.escape(params.activity_name.strip()), re.I)
        for item in scheduled_items:
            if pat.search(item.title_override or ""):
                target_item = item
                break
    elif params.day_number:
        day_items = [item for item in scheduled_items if item.day_number == params.day_number]
        if day_items:
            target_item = day_items[-1]  # remove last activity of that day

    if not target_item:
        return [], f"Could not find a matching activity to remove."

    title = target_item.title_override or "Activity"
    day_num = target_item.day_number
    db.delete(target_item)
    change = f"Removed '{title}' from Day {day_num}."
    return [change], f"Successfully removed '{title}' from Day {day_num}."


async def replan_replace_activity(
    trip: Trip,
    itinerary: Itinerary,
    params: AIActionParameters,
    mongo_db: AsyncIOMotorDatabase,
    db: Session,
) -> Tuple[List[str], str]:
    """Controlled activity replacement from MongoDB catalogue."""
    scheduled_items = db.query(ItineraryItem).filter(ItineraryItem.itinerary_id == itinerary.id).all()
    if not scheduled_items:
        return [], "There are no activities in your itinerary to replace."

    # Identify item to replace
    target_item = None
    if params.current_activity_name:
        pat = re.compile(re.escape(params.current_activity_name.strip()), re.I)
        for item in scheduled_items:
            if pat.search(item.title_override or ""):
                target_item = item
                break
    elif params.item_id:
        for item in scheduled_items:
            if item.id == params.item_id:
                target_item = item
                break
    elif params.day_number:
        day_items = [item for item in scheduled_items if item.day_number == params.day_number]
        if day_items:
            target_item = day_items[0]

    if not target_item:
        target_item = scheduled_items[0]

    # Find replacement in MongoDB
    dest_doc = await _fetch_destination_document(trip.destination, mongo_db)
    dest_id = str(dest_doc["_id"]) if dest_doc else None
    all_acts = await _fetch_matching_activities(trip.destination, dest_id, mongo_db)
    scheduled_ids = {item.activity_id for item in scheduled_items if item.activity_id}

    replacement = None
    if params.new_activity_name:
        pat = re.compile(re.escape(params.new_activity_name.strip()), re.I)
        for a in all_acts:
            if pat.search(a.get("name", "")) and str(a["_id"]) not in scheduled_ids:
                replacement = a
                break
        if not replacement:
            replacement = await mongo_db["activities"].find_one({"name": pat})
    elif params.category:
        cat_pat = re.compile(re.escape(params.category.strip()), re.I)
        matching_cats = [a for a in all_acts if cat_pat.search(a.get("category", "")) and str(a["_id"]) not in scheduled_ids]
        if matching_cats:
            matching_cats.sort(key=lambda a: float(a.get("rating", 0.0)), reverse=True)
            replacement = matching_cats[0]
    else:
        candidates = [a for a in all_acts if str(a["_id"]) not in scheduled_ids]
        if candidates:
            candidates.sort(key=lambda a: float(a.get("rating", 0.0)), reverse=True)
            replacement = candidates[0]

    if not replacement:
        return [], "Could not find a suitable replacement activity in the catalogue."

    old_name = target_item.title_override or "Activity"
    travellers = max(1, trip.travellers or 1)
    target_item.activity_id = str(replacement["_id"])
    target_item.title_override = replacement.get("name")
    target_item.estimated_cost = float(replacement.get("price", 0.0)) * travellers
    change = f"Replaced '{old_name}' with '{replacement.get('name')}' on Day {target_item.day_number}."
    return [change], f"Replaced '{old_name}' with '{replacement.get('name')}'."


async def replan_more_adventure(
    trip: Trip,
    itinerary: Itinerary,
    params: AIActionParameters,
    mongo_db: AsyncIOMotorDatabase,
    db: Session,
) -> Tuple[List[str], str]:
    """Controlled replanning to add high-adrenaline/adventure activities from catalogue."""
    dest_doc = await _fetch_destination_document(trip.destination, mongo_db)
    dest_id = str(dest_doc["_id"]) if dest_doc else None
    all_acts = await _fetch_matching_activities(trip.destination, dest_id, mongo_db)

    scheduled_items = db.query(ItineraryItem).filter(ItineraryItem.itinerary_id == itinerary.id).all()
    scheduled_ids = {item.activity_id for item in scheduled_items if item.activity_id}

    adv_acts = [
        a for a in all_acts
        if (a.get("category", "").lower() == "adventure" or any(kw in a.get("name", "").lower() for kw in ["scuba", "trek", "rafting", "kayak", "safari", "diving"]))
        and str(a["_id"]) not in scheduled_ids
    ]

    if not adv_acts:
        return [], f"No additional adventure activities available in the catalogue for {trip.destination}."

    adv_acts.sort(key=lambda a: float(a.get("rating", 0.0)), reverse=True)
    best_adv = adv_acts[0]

    # Add as new activity or replace non-adventure
    total_days = max(1, (trip.end_date - trip.start_date).days)
    travellers = max(1, trip.travellers or 1)

    if len(scheduled_items) < total_days * 2:
        # Add to day with fewest activities
        day_counts = {d: 0 for d in range(1, total_days + 1)}
        for item in scheduled_items:
            if item.day_number in day_counts:
                day_counts[item.day_number] += 1
        target_day = min(day_counts, key=day_counts.get)
        new_item = ItineraryItem(
            itinerary_id=itinerary.id,
            day_number=target_day,
            time_slot="morning",
            activity_id=str(best_adv["_id"]),
            title_override=best_adv.get("name"),
            start_time="09:30",
            duration_minutes=int(best_adv.get("duration_hours", 2) * 60),
            estimated_cost=float(best_adv.get("price", 0.0)) * travellers,
        )
        db.add(new_item)
        change = f"Added adventure activity '{best_adv.get('name')}' to Day {target_day}."
    else:
        # Replace the lowest-rated activity
        scheduled_items.sort(key=lambda item: float(item.estimated_cost or 0.0))
        target_item = scheduled_items[0]
        old_title = target_item.title_override or "Activity"
        target_item.activity_id = str(best_adv["_id"])
        target_item.title_override = best_adv.get("name")
        target_item.estimated_cost = float(best_adv.get("price", 0.0)) * travellers
        change = f"Replaced '{old_title}' with adventure activity '{best_adv.get('name')}' on Day {target_item.day_number}."

    return [change], f"Injected adventure into your itinerary with '{best_adv.get('name')}'."


async def replan_more_relaxed(
    trip: Trip,
    itinerary: Itinerary,
    params: AIActionParameters,
    mongo_db: AsyncIOMotorDatabase,
    db: Session,
) -> Tuple[List[str], str]:
    """Controlled replanning to reduce pace and free up time."""
    scheduled_items = db.query(ItineraryItem).filter(ItineraryItem.itinerary_id == itinerary.id).all()
    if not scheduled_items:
        return [], "Your itinerary is already empty."

    changes_made = []
    if params.day_number:
        # Make specific day relaxed (keep at most 1 activity)
        day_items = [item for item in scheduled_items if item.day_number == params.day_number]
        if len(day_items) > 1:
            for item in day_items[1:]:
                db.delete(item)
                changes_made.append(f"Removed '{item.title_override}' to relax Day {params.day_number}.")
    else:
        # Check all days: if any day has 3 activities, remove the evening one; or if 2, remove the afternoon one
        by_day = {}
        for item in scheduled_items:
            by_day.setdefault(item.day_number, []).append(item)

        for day_num, items in by_day.items():
            if len(items) >= 2:
                to_remove = items[-1]
                db.delete(to_remove)
                changes_made.append(f"Freed up schedule on Day {day_num} by removing '{to_remove.title_override}'.")
                break

    if not changes_made:
        return [], "Your itinerary is already comfortably paced."

    return changes_made, "Adjusted your schedule for a more relaxed and spacious trip."


async def replan_weather_safe(
    trip: Trip,
    itinerary: Itinerary,
    params: AIActionParameters,
    mongo_db: AsyncIOMotorDatabase,
    db: Session,
) -> Tuple[List[str], str]:
    """Controlled replanning to swap rain-unfriendly activities with indoor/cultural ones."""
    scheduled_items = db.query(ItineraryItem).filter(ItineraryItem.itinerary_id == itinerary.id).all()
    if not scheduled_items:
        return [], "No activities scheduled to adjust."

    dest_doc = await _fetch_destination_document(trip.destination, mongo_db)
    dest_id = str(dest_doc["_id"]) if dest_doc else None
    all_acts = await _fetch_matching_activities(trip.destination, dest_id, mongo_db)

    scheduled_ids = {item.activity_id for item in scheduled_items if item.activity_id}

    # Available rain safe catalogue activities
    rain_safe_acts = [
        a for a in all_acts
        if (a.get("category", "").lower() in RAIN_SAFE_CATEGORIES or any(kw in a.get("name", "").lower() for kw in RAIN_SAFE_CATEGORIES))
        and str(a["_id"]) not in scheduled_ids
    ]
    rain_safe_acts.sort(key=lambda a: float(a.get("rating", 0.0)), reverse=True)

    changes_made = []
    travellers = max(1, trip.travellers or 1)

    for item in scheduled_items:
        title = (item.title_override or "").lower()
        is_unfriendly = any(kw in title for kw in RAIN_UNFRIENDLY_CATEGORIES)
        if is_unfriendly and rain_safe_acts:
            sub = rain_safe_acts.pop(0)
            old_title = item.title_override or "Activity"
            item.activity_id = str(sub["_id"])
            item.title_override = sub.get("name")
            item.estimated_cost = float(sub.get("price", 0.0)) * travellers
            scheduled_ids.add(str(sub["_id"]))
            changes_made.append(f"Swapped outdoor activity '{old_title}' with weather-safe '{sub.get('name')}' on Day {item.day_number}.")

    if not changes_made:
        return [], "All scheduled activities are already indoor or weather-safe."

    return changes_made, f"Adjusted {len(changes_made)} activity(ies) to weather-safe indoor alternatives."


async def replan_explain_itinerary(
    trip: Trip,
    itinerary: Itinerary,
    mongo_db: AsyncIOMotorDatabase,
    db: Session,
) -> Tuple[List[str], str]:
    """Provide a grounded, comprehensive summary and rationale for the itinerary without modifying anything."""
    from bson import ObjectId

    # Hotel details
    hotel_info = "No hotel selected."
    if itinerary.selected_hotel_id:
        try:
            h = await mongo_db["hotels"].find_one({"_id": ObjectId(itinerary.selected_hotel_id)})
            if h:
                hotel_info = f"{h.get('name')} ({h.get('rating', 'N/A')}★, ₹{h.get('price_per_night', 0)}/night)"
        except Exception:
            pass

    # Flights details
    flight_parts = []
    if itinerary.outbound_flight_id:
        flight_parts.append("Outbound flight confirmed")
    if itinerary.return_flight_id:
        flight_parts.append("Return flight confirmed")
    flight_info = " & ".join(flight_parts) if flight_parts else "Flights pending"

    # Activities details
    items = db.query(ItineraryItem).filter(ItineraryItem.itinerary_id == itinerary.id).all()
    act_count = len(items)
    days = max(1, (trip.end_date - trip.start_date).days)

    explanation = (
        f"Your {days}-day trip to {trip.destination} is planned with {act_count} activity(ies). "
        f"Accommodation is set at {hotel_info}. Flight status: {flight_info}. "
        f"Total estimated cost is ₹{itinerary.estimated_total_cost:,.2f} against your ₹{trip.budget:,.2f} budget."
    )
    return [], explanation


async def execute_ai_replanning(
    trip: Trip,
    itinerary: Itinerary,
    user_message: str,
    llm_provider: LLMProvider,
    mongo_db: AsyncIOMotorDatabase,
    db: Session,
) -> AIChatResponse:
    """
    Main dispatcher for AI chat & replanning.
    Enforces interpret-first, validate, execute, recalculate, commit or rollback.
    """
    # 1. Capture initial baseline cost
    previous_total = await recalculate_itinerary_cost(itinerary, trip, mongo_db, db)

    def _build_response(intent_str: str, status: str, message: str, changes: List[str] = None):
        changes = changes or []
        updated_total = itinerary.estimated_total_cost
        diff = round(updated_total - previous_total, 2)
        savings = max(0.0, round(previous_total - updated_total, 2))
        comp = BudgetComparison(
            previous_total=round(previous_total, 2),
            updated_total=round(updated_total, 2),
            difference=diff,
            savings=savings,
            currency=trip.currency or "INR",
        )
        itinerary_resp = ItineraryResponse.model_validate(itinerary) if status != "error" else None
        return AIChatResponse(
            trip_id=trip.id,
            intent=intent_str,
            status=status,
            message=message,
            changes_made=changes,
            budget_comparison=comp,
            itinerary=itinerary_resp,
        )

    # 2. Check AI provider availability
    if not llm_provider.enabled:
        return _build_response(
            intent_str=SupportedIntent.UNKNOWN.value,
            status="error",
            message="AI provider is not configured or available. Itinerary remains unchanged.",
        )

    # 3. LLM Interpretation
    try:
        raw_json = await llm_provider.structured_json(SYSTEM_PROMPT, user_message)
    except Exception as e:
        logger.error("LLM Provider call threw an exception: %s", e)
        return _build_response(
            intent_str=SupportedIntent.UNKNOWN.value,
            status="error",
            message="AI provider encountered an error. Itinerary remains unchanged.",
        )

    if raw_json is None:
        return _build_response(
            intent_str=SupportedIntent.UNKNOWN.value,
            status="error",
            message="AI provider returned an empty response or is unavailable. Itinerary remains unchanged.",
        )

    # 4. Strict Schema Validation
    try:
        action = AIStructuredAction.model_validate(raw_json)
    except ValidationError as ve:
        logger.warning("LLM output validation error: %s", ve)
        return _build_response(
            intent_str=SupportedIntent.UNKNOWN.value,
            status="error",
            message="AI returned an invalid or malformed action structure. Itinerary remains unchanged.",
        )

    # 5. Handle Unknown or Unsupported Intent
    if action.intent == SupportedIntent.UNKNOWN:
        return _build_response(
            intent_str=SupportedIntent.UNKNOWN.value,
            status="unsupported",
            message=(
                "I could not map your request to a supported travel planning action. "
                "You can ask me to make the trip cheaper, change hotel, add or remove activities, "
                "add more adventure, make the plan more relaxed, switch to weather-safe activities, "
                "or explain your itinerary."
            ),
        )

    # 6. Transactional Replanning Execution
    try:
        changes: List[str] = []
        msg: str = ""

        if action.intent == SupportedIntent.MAKE_TRIP_CHEAPER:
            changes, msg = await replan_cheaper_trip(trip, itinerary, action.parameters, mongo_db, db)
        elif action.intent == SupportedIntent.CHANGE_HOTEL:
            changes, msg = await replan_hotel(trip, itinerary, action.parameters, mongo_db, db)
        elif action.intent == SupportedIntent.ADD_ACTIVITY:
            changes, msg = await replan_add_activity(trip, itinerary, action.parameters, mongo_db, db)
        elif action.intent == SupportedIntent.REMOVE_ACTIVITY:
            changes, msg = await replan_remove_activity(trip, itinerary, action.parameters, mongo_db, db)
        elif action.intent == SupportedIntent.REPLACE_ACTIVITY:
            changes, msg = await replan_replace_activity(trip, itinerary, action.parameters, mongo_db, db)
        elif action.intent == SupportedIntent.MORE_ADVENTURE:
            changes, msg = await replan_more_adventure(trip, itinerary, action.parameters, mongo_db, db)
        elif action.intent == SupportedIntent.MORE_RELAXED:
            changes, msg = await replan_more_relaxed(trip, itinerary, action.parameters, mongo_db, db)
        elif action.intent == SupportedIntent.WEATHER_SAFE_PLAN:
            changes, msg = await replan_weather_safe(trip, itinerary, action.parameters, mongo_db, db)
        elif action.intent == SupportedIntent.EXPLAIN_ITINERARY:
            changes, msg = await replan_explain_itinerary(trip, itinerary, mongo_db, db)
            return _build_response(intent_str=action.intent.value, status="explained", message=msg, changes=[])

        # Recalculate cost after mutations
        await recalculate_itinerary_cost(itinerary, trip, mongo_db, db)

        if changes:
            db.commit()
            db.refresh(itinerary)
            return _build_response(intent_str=action.intent.value, status="applied", message=msg, changes=changes)
        else:
            db.rollback()
            return _build_response(intent_str=action.intent.value, status="no_change", message=msg, changes=[])

    except Exception as e:
        logger.error("Error executing replanning action: %s", e, exc_info=True)
        db.rollback()
        return _build_response(
            intent_str=action.intent.value,
            status="error",
            message=f"Failed to apply replanning action: {str(e)}. Itinerary remains unchanged.",
        )
