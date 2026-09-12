from unittest.mock import patch, AsyncMock
from uuid import uuid4
import pytest
from fastapi import HTTPException

from app.core.database import SessionLocal
from app.models.itinerary import Itinerary, ItineraryItem
from app.schemas.weather import WeatherResponse
from datetime import datetime, timezone


async def register_and_login(client, name: str):
    email = f"{name.lower()}-{uuid4().hex}@odyssey.com"
    reg = await client.post(
        "/api/v1/users/",
        params={"name": name, "email": email, "password": "password123"},
    )
    assert reg.status_code == 200
    user_id = reg.json()["user_id"]

    login = await client.post(
        "/api/v1/users/login",
        params={"email": email, "password": "password123"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    return headers, user_id


async def create_trip(client, headers, **overrides):
    payload = {
        "from_city": "Delhi",
        "destination": "Goa",
        "start_date": "2026-06-01",
        "end_date": "2026-06-04",  # 3 days
        "travellers": 2,
        "budget": 40000.0,
        "currency": "INR",
        "interests": ["Beach", "Adventure"],
        "hotel_rating": 4,
        "pace": "moderate",
        "avoid_crowds": False,
    }
    payload.update(overrides)
    res = await client.post("/api/v1/trips/plan", json=payload, headers=headers)
    assert res.status_code == 200
    return res.json()["trip_id"]


async def seed_tourism_catalogue(mock_mongo_db, dest_name="Goa"):
    # 1. Destination with coordinates
    dest_res = await mock_mongo_db["destinations"].insert_one({
        "name": dest_name,
        "country": "India",
        "city": dest_name,
        "latitude": 15.4989,
        "longitude": 73.8278,
    })
    dest_id = str(dest_res.inserted_id)

    # 2. Hotels
    h1 = await mock_mongo_db["hotels"].insert_one({
        "destination_id": dest_id,
        "name": "Luxury Beach Resort",
        "price_per_night": 4500.0,
        "rating": 4.6,
        "currency": "INR",
        "available_rooms": 8,
    })
    h2 = await mock_mongo_db["hotels"].insert_one({
        "destination_id": dest_id,
        "name": "Budget City Inn",
        "price_per_night": 1500.0,
        "rating": 3.2,
        "currency": "INR",
        "available_rooms": 20,
    })

    # 3. Flights
    f1 = await mock_mongo_db["flights"].insert_one({
        "origin": "DEL",
        "destination": "GOA",
        "airline": "IndiGo",
        "flight_number": "6E-201",
        "departure_time": "2026-06-01T09:00:00Z",
        "arrival_time": "2026-06-01T11:30:00Z",
        "price": 3200.0,
        "currency": "INR",
        "stops": 0,
    })
    f2 = await mock_mongo_db["flights"].insert_one({
        "origin": "GOA",
        "destination": "DEL",
        "airline": "Air India",
        "flight_number": "AI-502",
        "departure_time": "2026-06-04T17:00:00Z",
        "arrival_time": "2026-06-04T19:30:00Z",
        "price": 3500.0,
        "currency": "INR",
        "stops": 0,
    })

    # 4. Activities
    a1 = await mock_mongo_db["activities"].insert_one({
        "destination_id": dest_id,
        "name": "Scuba Diving Expedition",
        "category": "Adventure",
        "description": "Thrilling underwater exploration",
        "price": 1800.0,
        "rating": 4.8,
        "duration_minutes": 180,
    })
    a2 = await mock_mongo_db["activities"].insert_one({
        "destination_id": dest_id,
        "name": "Heritage Church & Fort Tour",
        "category": "Heritage",
        "description": "Historical walking tour exploring Old Goa",
        "price": 600.0,
        "rating": 4.7,
        "duration_minutes": 120,
    })
    a3 = await mock_mongo_db["activities"].insert_one({
        "destination_id": dest_id,
        "name": "Goan Spice Plantation & Lunch",
        "category": "Culinary",
        "description": "Organic farm tour with traditional Goan lunch",
        "price": 850.0,
        "rating": 4.6,
        "duration_minutes": 150,
    })
    a4 = await mock_mongo_db["activities"].insert_one({
        "destination_id": dest_id,
        "name": "Water Sports Combo",
        "category": "Water Sports",
        "description": "Parasailing, jet ski and banana ride",
        "price": 2000.0,
        "rating": 4.5,
        "duration_minutes": 120,
    })

    return {
        "dest_id": dest_id,
        "hotel_ids": [str(h1.inserted_id), str(h2.inserted_id)],
        "flight_ids": [str(f1.inserted_id), str(f2.inserted_id)],
        "activity_ids": [str(a1.inserted_id), str(a2.inserted_id), str(a3.inserted_id), str(a4.inserted_id)],
    }


# 1. Normal itinerary generation
@pytest.mark.asyncio
async def test_normal_itinerary_generation(client, mock_mongo_db):
    headers, _ = await register_and_login(client, "NormalGen")
    trip_id = await create_trip(client, headers)
    cat = await seed_tourism_catalogue(mock_mongo_db, "Goa")

    with patch("app.services.itinerary_generator_service.get_weather_forecast") as mock_weather:
        mock_weather.return_value = WeatherResponse(
            latitude=15.49,
            longitude=73.82,
            temperature=30.0,
            condition="Mainly clear",
            weather_code=1,
            unit="Celsius",
            timestamp=datetime.now(timezone.utc)
        )
        res = await client.post(f"/api/v1/trips/{trip_id}/generate", headers=headers)

    assert res.status_code == 200
    data = res.json()
    assert data["message"] == "Itinerary generated successfully"
    assert data["trip_id"] == trip_id

    # Itinerary checks
    itinerary = data["itinerary"]
    assert itinerary["selected_hotel_id"] == cat["hotel_ids"][0]  # Luxury Beach Resort picked (preferred rating 4)
    assert itinerary["outbound_flight_id"] == cat["flight_ids"][0]
    assert itinerary["return_flight_id"] == cat["flight_ids"][1]
    assert len(itinerary["items"]) > 0

    # Budget summary checks
    budget = data["budget_summary"]
    assert budget["total_budget"] == 40000.0
    assert budget["estimated_total_cost"] == itinerary["estimated_total_cost"]
    assert budget["breakdown"]["hotel_cost"] > 0
    assert budget["breakdown"]["flights_cost"] > 0
    assert budget["breakdown"]["activities_cost"] > 0

    # Weather summary checks
    assert data["weather_summary"]["available"] is True
    assert data["weather_summary"]["is_rainy"] is False


# 2. Ownership enforcement (unauthenticated and cross-user)
@pytest.mark.asyncio
async def test_generator_ownership_enforcement(client, mock_mongo_db):
    headers_a, _ = await register_and_login(client, "OwnerA")
    headers_b, _ = await register_and_login(client, "OtherB")
    trip_id_a = await create_trip(client, headers_a)

    # Unauthenticated returns 401
    unauth = await client.post(f"/api/v1/trips/{trip_id_a}/generate")
    assert unauth.status_code == 401

    # Cross-user returns 404
    cross = await client.post(f"/api/v1/trips/{trip_id_a}/generate", headers=headers_b)
    assert cross.status_code == 404
    assert cross.json()["detail"] == "Trip not found"


# 3. Invalid trip returns 404
@pytest.mark.asyncio
async def test_generator_invalid_trip(client, mock_mongo_db):
    headers, _ = await register_and_login(client, "InvalidTripUser")
    res = await client.post("/api/v1/trips/999999/generate", headers=headers)
    assert res.status_code == 404


# 4. Low budget warning
@pytest.mark.asyncio
async def test_generator_low_budget_warning(client, mock_mongo_db):
    headers, _ = await register_and_login(client, "LowBudgetUser")
    # Low budget of 5000 for 2 travellers and 3 nights
    trip_id = await create_trip(client, headers, budget=5000.0)
    await seed_tourism_catalogue(mock_mongo_db, "Goa")

    res = await client.post(f"/api/v1/trips/{trip_id}/generate", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["budget_summary"]["is_over_budget"] is True
    assert data["budget_summary"]["over_budget_amount"] > 0
    assert any("exceeds trip budget" in w for w in data["warnings"])


# 5. Relaxed pace generates 1 activity per day
@pytest.mark.asyncio
async def test_generator_relaxed_pace(client, mock_mongo_db):
    headers, _ = await register_and_login(client, "RelaxedUser")
    # 3 days trip with relaxed pace
    trip_id = await create_trip(client, headers, pace="relaxed")
    await seed_tourism_catalogue(mock_mongo_db, "Goa")

    res = await client.post(f"/api/v1/trips/{trip_id}/generate", headers=headers)
    assert res.status_code == 200
    items = res.json()["itinerary"]["items"]
    # Exactly 1 activity per day for 3 days = 3 items
    assert len(items) == 3
    days = [item["day_number"] for item in items]
    assert days == [1, 2, 3]
    assert all(item["time_slot"] == "morning" for item in items)


# 6. Active (fast) pace generates up to 3 activities per day
@pytest.mark.asyncio
async def test_generator_fast_pace(client, mock_mongo_db):
    headers, _ = await register_and_login(client, "ActiveUser")
    # 2 days trip with active pace
    trip_id = await create_trip(client, headers, pace="active", end_date="2026-06-03")
    await seed_tourism_catalogue(mock_mongo_db, "Goa")

    res = await client.post(f"/api/v1/trips/{trip_id}/generate", headers=headers)
    assert res.status_code == 200
    items = res.json()["itinerary"]["items"]
    # 2 days * 3 slots = 6 items
    assert len(items) == 6
    slots = [item["time_slot"] for item in items]
    assert "morning" in slots
    assert "afternoon" in slots
    assert "evening" in slots


# 7. Interests affect activity selection
@pytest.mark.asyncio
async def test_generator_interests_affect_activity_selection(client, mock_mongo_db):
    headers, _ = await register_and_login(client, "InterestUser")
    cat = await seed_tourism_catalogue(mock_mongo_db, "Goa")

    # Trip 1: Food / Culinary interest
    trip_food = await create_trip(client, headers, interests=["Food", "Culinary"], pace="relaxed")
    res_food = await client.post(f"/api/v1/trips/{trip_food}/generate", headers=headers)
    assert res_food.status_code == 200
    food_items = res_food.json()["itinerary"]["items"]
    # First activity should be the Spice Plantation & Lunch (Culinary)
    assert food_items[0]["activity_id"] == cat["activity_ids"][2]

    # Trip 2: Adventure interest
    trip_adv = await create_trip(client, headers, interests=["Adventure"], pace="relaxed")
    res_adv = await client.post(f"/api/v1/trips/{trip_adv}/generate", headers=headers)
    assert res_adv.status_code == 200
    adv_items = res_adv.json()["itinerary"]["items"]
    # First activity should be Scuba Diving (Adventure)
    assert adv_items[0]["activity_id"] == cat["activity_ids"][0]


# 8. Rain weather prioritizes indoor/rain-safe activities
@pytest.mark.asyncio
async def test_generator_rain_weather_prioritizes_indoor(client, mock_mongo_db):
    headers, _ = await register_and_login(client, "RainUser")
    cat = await seed_tourism_catalogue(mock_mongo_db, "Goa")
    trip_id = await create_trip(client, headers, pace="relaxed", interests=[])

    with patch("app.services.itinerary_generator_service.get_weather_forecast") as mock_weather:
        mock_weather.return_value = WeatherResponse(
            latitude=15.49,
            longitude=73.82,
            temperature=24.0,
            condition="Heavy rain",
            weather_code=65,  # Rain
            unit="Celsius",
            timestamp=datetime.now(timezone.utc)
        )
        res = await client.post(f"/api/v1/trips/{trip_id}/generate", headers=headers)

    assert res.status_code == 200
    data = res.json()
    assert data["weather_summary"]["is_rainy"] is True
    assert data["weather_summary"]["rain_safe_prioritized"] is True
    assert any("Rain or adverse weather detected" in w for w in data["warnings"])

    items = data["itinerary"]["items"]
    # Indoor/heritage activities should be picked first over outdoor water sports / scuba
    top_activity_id = items[0]["activity_id"]
    # Church & Fort Tour (Heritage) or Spice Plantation (Culinary) prioritized over Scuba Diving
    assert top_activity_id in [cat["activity_ids"][1], cat["activity_ids"][2]]


# 9. Unavailable weather gracefully continues
@pytest.mark.asyncio
async def test_generator_unavailable_weather(client, mock_mongo_db):
    headers, _ = await register_and_login(client, "NoWeatherUser")
    await seed_tourism_catalogue(mock_mongo_db, "Goa")
    trip_id = await create_trip(client, headers)

    with patch("app.services.itinerary_generator_service.get_weather_forecast") as mock_weather:
        mock_weather.side_effect = HTTPException(status_code=503, detail="Weather provider offline")
        res = await client.post(f"/api/v1/trips/{trip_id}/generate", headers=headers)

    assert res.status_code == 200
    data = res.json()
    assert data["weather_summary"]["available"] is False
    assert len(data["itinerary"]["items"]) > 0


# 10. No matching hotel in catalogue
@pytest.mark.asyncio
async def test_generator_no_matching_hotel(client, mock_mongo_db):
    headers, _ = await register_and_login(client, "NoHotelUser")
    # Destination without any seeded hotels
    trip_id = await create_trip(client, headers, destination="NowhereLand")

    res = await client.post(f"/api/v1/trips/{trip_id}/generate", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["itinerary"]["selected_hotel_id"] is None
    assert any("No hotels found matching destination" in w for w in data["warnings"])


# 11. No matching activities in catalogue
@pytest.mark.asyncio
async def test_generator_no_matching_activities(client, mock_mongo_db):
    headers, _ = await register_and_login(client, "NoActUser")
    trip_id = await create_trip(client, headers, destination="EmptyCity")

    res = await client.post(f"/api/v1/trips/{trip_id}/generate", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert len(data["itinerary"]["items"]) == 0
    assert any("No activities found matching destination" in w for w in data["warnings"])


# 12. Persisted itinerary retrieval after generation
@pytest.mark.asyncio
async def test_persisted_itinerary_retrieval_after_generation(client, mock_mongo_db):
    headers, _ = await register_and_login(client, "PersistenceVerifyUser")
    trip_id = await create_trip(client, headers)
    await seed_tourism_catalogue(mock_mongo_db, "Goa")

    gen_res = await client.post(f"/api/v1/trips/{trip_id}/generate", headers=headers)
    assert gen_res.status_code == 200
    gen_itinerary = gen_res.json()["itinerary"]

    # Retrieve via GET /api/v1/trips/{trip_id}/itinerary
    get_res = await client.get(f"/api/v1/trips/{trip_id}/itinerary", headers=headers)
    assert get_res.status_code == 200
    get_itinerary = get_res.json()

    assert get_itinerary["id"] == gen_itinerary["id"]
    assert get_itinerary["selected_hotel_id"] == gen_itinerary["selected_hotel_id"]
    assert get_itinerary["outbound_flight_id"] == gen_itinerary["outbound_flight_id"]
    assert get_itinerary["return_flight_id"] == gen_itinerary["return_flight_id"]
    assert get_itinerary["estimated_total_cost"] == gen_itinerary["estimated_total_cost"]
    assert len(get_itinerary["items"]) == len(gen_itinerary["items"])

    # Verify directly in SQLite DB
    with SessionLocal() as db:
        itin_db = db.query(Itinerary).filter(Itinerary.trip_id == trip_id).first()
        assert itin_db is not None
        assert itin_db.selected_hotel_id == gen_itinerary["selected_hotel_id"]
        assert len(itin_db.items) == len(gen_itinerary["items"])
