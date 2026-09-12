from uuid import uuid4
import pytest
from app.core.database import SessionLocal
from app.models.itinerary import Itinerary, ItineraryItem
from app.models.trip import Trip


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


async def create_trip(client, headers, travellers: int = 2, days: int = 3):
    res = await client.post(
        "/api/v1/trips/plan",
        json={
            "from_city": "Delhi",
            "destination": "Goa",
            "start_date": "2026-06-01",
            "end_date": f"2026-06-0{1 + days}",
            "travellers": travellers,
            "budget": 50000.0,
            "currency": "INR",
            "interests": ["Beach", "Adventure"],
        },
        headers=headers,
    )
    assert res.status_code == 200
    return res.json()["trip_id"]


async def seed_hotel(mock_mongo_db, name="Seaside Resort", price_per_night=4000.0):
    result = await mock_mongo_db["hotels"].insert_one({
        "destination_id": "dest-goa",
        "name": name,
        "price_per_night": price_per_night,
        "currency": "INR",
        "rating": 4.5,
    })
    return str(result.inserted_id)


async def seed_flight(mock_mongo_db, flight_number="6E-101", price=3500.0):
    result = await mock_mongo_db["flights"].insert_one({
        "origin": "DEL",
        "destination": "GOA",
        "airline": "IndiGo",
        "flight_number": flight_number,
        "departure_time": "2026-06-01T08:00:00Z",
        "arrival_time": "2026-06-01T10:30:00Z",
        "duration_minutes": 150,
        "price": price,
        "currency": "INR",
    })
    return str(result.inserted_id)


async def seed_activity(mock_mongo_db, name="Parasailing Adventure", price=1500.0, duration=90):
    result = await mock_mongo_db["activities"].insert_one({
        "destination_id": "dest-goa",
        "name": name,
        "category": "Adventure",
        "price": price,
        "duration_minutes": duration,
        "currency": "INR",
        "rating": 4.7,
    })
    return str(result.inserted_id)


# 1. Create / retrieve itinerary structure
@pytest.mark.asyncio
async def test_get_or_create_itinerary_structure(client, mock_mongo_db):
    headers, _ = await register_and_login(client, "ItineraryUser")
    trip_id = await create_trip(client, headers)

    res = await client.get(f"/api/v1/trips/{trip_id}/itinerary", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["trip_id"] == trip_id
    assert "id" in data
    assert "selected_hotel_id" in data
    assert "outbound_flight_id" in data
    assert "return_flight_id" in data
    assert data["estimated_total_cost"] == 0.0
    assert isinstance(data["items"], list)
    assert len(data["items"]) == 0

    # Verify persistent record in SQLite
    with SessionLocal() as db:
        itin = db.query(Itinerary).filter(Itinerary.trip_id == trip_id).first()
        assert itin is not None
        assert itin.trip.id == trip_id


# 2. Authenticated ownership (unauthenticated returns 401)
@pytest.mark.asyncio
async def test_authenticated_ownership(client, mock_mongo_db):
    headers, _ = await register_and_login(client, "AuthOwner")
    trip_id = await create_trip(client, headers)

    # Missing auth header
    res1 = await client.get(f"/api/v1/trips/{trip_id}/itinerary")
    assert res1.status_code == 401

    res2 = await client.put(f"/api/v1/trips/{trip_id}/hotel", json={"hotel_id": "dummy"})
    assert res2.status_code == 401

    res3 = await client.put(f"/api/v1/trips/{trip_id}/flights", json={})
    assert res3.status_code == 401

    res4 = await client.put(f"/api/v1/trips/{trip_id}/activities", json={"action": "add"})
    assert res4.status_code == 401


# 3. Invalid trip ID returns 404
@pytest.mark.asyncio
async def test_invalid_trip_returns_404(client, mock_mongo_db):
    headers, _ = await register_and_login(client, "InvalidTripUser")
    res = await client.get("/api/v1/trips/999999/itinerary", headers=headers)
    assert res.status_code == 404
    assert res.json()["detail"] == "Trip not found"


# 4. Unauthorized trip (User A cannot access or mutate User B's itinerary)
@pytest.mark.asyncio
async def test_unauthorized_trip_access(client, mock_mongo_db):
    headers_a, _ = await register_and_login(client, "OwnerA")
    headers_b, _ = await register_and_login(client, "AttackerB")

    trip_id_a = await create_trip(client, headers_a)

    # User B cannot read User A's itinerary
    get_res = await client.get(f"/api/v1/trips/{trip_id_a}/itinerary", headers=headers_b)
    assert get_res.status_code == 404

    # User B cannot set hotel on User A's itinerary
    hotel_id = await seed_hotel(mock_mongo_db)
    put_res = await client.put(f"/api/v1/trips/{trip_id_a}/hotel", json={"hotel_id": hotel_id}, headers=headers_b)
    assert put_res.status_code == 404


# 5. Invalid hotel ID (bad hex format or non-existent in catalogue)
@pytest.mark.asyncio
async def test_invalid_hotel_id(client, mock_mongo_db):
    headers, _ = await register_and_login(client, "HotelValUser")
    trip_id = await create_trip(client, headers)

    # Malformed hex ObjectId
    bad_format = await client.put(f"/api/v1/trips/{trip_id}/hotel", json={"hotel_id": "not-a-valid-hex"}, headers=headers)
    assert bad_format.status_code == 400
    assert "Invalid hotel ID format" in bad_format.json()["detail"]

    # Valid hex format but non-existent in MongoDB
    non_existent = await client.put(f"/api/v1/trips/{trip_id}/hotel", json={"hotel_id": "507f1f77bcf86cd799439011"}, headers=headers)
    assert non_existent.status_code == 404
    assert "not found in catalogue" in non_existent.json()["detail"]


# 6. Invalid flight ID (bad format or non-existent)
@pytest.mark.asyncio
async def test_invalid_flight_id(client, mock_mongo_db):
    headers, _ = await register_and_login(client, "FlightValUser")
    trip_id = await create_trip(client, headers)

    # Malformed format
    bad_format = await client.put(
        f"/api/v1/trips/{trip_id}/flights",
        json={"outbound_flight_id": "invalid-flight-id"},
        headers=headers,
    )
    assert bad_format.status_code == 400

    # Non-existent in catalogue
    non_existent = await client.put(
        f"/api/v1/trips/{trip_id}/flights",
        json={"outbound_flight_id": "507f1f77bcf86cd799439012"},
        headers=headers,
    )
    assert non_existent.status_code == 404
    assert "not found in catalogue" in non_existent.json()["detail"]


# 7. Invalid activity ID (bad format or non-existent)
@pytest.mark.asyncio
async def test_invalid_activity_id(client, mock_mongo_db):
    headers, _ = await register_and_login(client, "ActivityValUser")
    trip_id = await create_trip(client, headers)

    # Malformed format
    bad_format = await client.put(
        f"/api/v1/trips/{trip_id}/activities",
        json={"action": "add", "activity_id": "bad-hex-id", "day_number": 1},
        headers=headers,
    )
    assert bad_format.status_code == 400

    # Non-existent
    non_existent = await client.put(
        f"/api/v1/trips/{trip_id}/activities",
        json={"action": "add", "activity_id": "507f1f77bcf86cd799439013", "day_number": 1},
        headers=headers,
    )
    assert non_existent.status_code == 404
    assert "not found in catalogue" in non_existent.json()["detail"]


# 8. Replace hotel
@pytest.mark.asyncio
async def test_replace_hotel(client, mock_mongo_db):
    headers, _ = await register_and_login(client, "HotelSwapUser")
    trip_id = await create_trip(client, headers, days=3)  # 3 nights

    hotel_1 = await seed_hotel(mock_mongo_db, name="Hotel 1", price_per_night=2000.0)
    hotel_2 = await seed_hotel(mock_mongo_db, name="Hotel 2", price_per_night=5000.0)

    # Set Hotel 1
    res1 = await client.put(f"/api/v1/trips/{trip_id}/hotel", json={"hotel_id": hotel_1}, headers=headers)
    assert res1.status_code == 200
    assert res1.json()["selected_hotel_id"] == hotel_1
    assert res1.json()["estimated_total_cost"] == 6000.0  # 2000 * 3 nights

    # Replace with Hotel 2
    res2 = await client.put(f"/api/v1/trips/{trip_id}/hotel", json={"hotel_id": hotel_2}, headers=headers)
    assert res2.status_code == 200
    assert res2.json()["selected_hotel_id"] == hotel_2
    assert res2.json()["estimated_total_cost"] == 15000.0  # 5000 * 3 nights


# 9. Add activity
@pytest.mark.asyncio
async def test_add_activity(client, mock_mongo_db):
    headers, _ = await register_and_login(client, "ActivityAddUser")
    trip_id = await create_trip(client, headers, travellers=2)

    act_id = await seed_activity(mock_mongo_db, name="Scuba Diving", price=1200.0, duration=120)

    res = await client.put(
        f"/api/v1/trips/{trip_id}/activities",
        json={
            "action": "add",
            "day_number": 1,
            "time_slot": "morning",
            "activity_id": act_id,
            "title_override": "Private Scuba Adventure",
            "start_time": "09:30",
        },
        headers=headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert len(data["items"]) == 1
    item = data["items"][0]
    assert item["activity_id"] == act_id
    assert item["day_number"] == 1
    assert item["time_slot"] == "morning"
    assert item["title_override"] == "Private Scuba Adventure"
    assert item["start_time"] == "09:30"
    assert item["duration_minutes"] == 120
    # Default cost = price * travellers = 1200 * 2 = 2400
    assert item["estimated_cost"] == 2400.0
    assert data["estimated_total_cost"] == 2400.0


# 10. Replace activity
@pytest.mark.asyncio
async def test_replace_activity(client, mock_mongo_db):
    headers, _ = await register_and_login(client, "ActivitySwapUser")
    trip_id = await create_trip(client, headers, travellers=1)

    act_1 = await seed_activity(mock_mongo_db, name="City Walking Tour", price=500.0)
    act_2 = await seed_activity(mock_mongo_db, name="Speedboat Cruise", price=2500.0)

    add_res = await client.put(
        f"/api/v1/trips/{trip_id}/activities",
        json={"action": "add", "day_number": 1, "activity_id": act_1},
        headers=headers,
    )
    item_id = add_res.json()["items"][0]["id"]
    assert add_res.json()["estimated_total_cost"] == 500.0

    # Replace activity on that item
    rep_res = await client.put(
        f"/api/v1/trips/{trip_id}/activities",
        json={"action": "replace", "item_id": item_id, "activity_id": act_2, "time_slot": "afternoon"},
        headers=headers,
    )
    assert rep_res.status_code == 200
    items = rep_res.json()["items"]
    assert len(items) == 1
    assert items[0]["activity_id"] == act_2
    assert items[0]["time_slot"] == "afternoon"
    assert rep_res.json()["estimated_total_cost"] == 2500.0


# 11. Remove activity
@pytest.mark.asyncio
async def test_remove_activity(client, mock_mongo_db):
    headers, _ = await register_and_login(client, "ActivityRemoveUser")
    trip_id = await create_trip(client, headers, travellers=1)

    act_1 = await seed_activity(mock_mongo_db, name="Museum Entry", price=300.0)
    act_2 = await seed_activity(mock_mongo_db, name="Sunset Cruise", price=1200.0)

    await client.put(
        f"/api/v1/trips/{trip_id}/activities",
        json={"action": "add", "day_number": 1, "activity_id": act_1},
        headers=headers,
    )
    add2 = await client.put(
        f"/api/v1/trips/{trip_id}/activities",
        json={"action": "add", "day_number": 2, "activity_id": act_2},
        headers=headers,
    )
    assert len(add2.json()["items"]) == 2
    assert add2.json()["estimated_total_cost"] == 1500.0

    # Remove first item
    item_1_id = add2.json()["items"][0]["id"]
    rem_res = await client.put(
        f"/api/v1/trips/{trip_id}/activities",
        json={"action": "remove", "item_id": item_1_id},
        headers=headers,
    )
    assert rem_res.status_code == 200
    assert len(rem_res.json()["items"]) == 1
    assert rem_res.json()["items"][0]["activity_id"] == act_2
    assert rem_res.json()["estimated_total_cost"] == 1200.0


# 12. Full cost recalculation (hotel + flights + activities)
@pytest.mark.asyncio
async def test_cost_recalculation(client, mock_mongo_db):
    headers, _ = await register_and_login(client, "CostCalcUser")
    # 2 travellers, 4 days (4 nights: June 1 to June 5)
    trip_id = await create_trip(client, headers, travellers=2, days=4)

    # Hotel: 3000/night * 4 nights = 12000
    hotel_id = await seed_hotel(mock_mongo_db, price_per_night=3000.0)
    # Outbound flight: 4000/ticket * 2 travellers = 8000
    outbound_id = await seed_flight(mock_mongo_db, flight_number="DEL-GOA", price=4000.0)
    # Return flight: 4500/ticket * 2 travellers = 9000
    return_id = await seed_flight(mock_mongo_db, flight_number="GOA-DEL", price=4500.0)
    # Activity 1: 1000 * 2 travellers = 2000
    act_1 = await seed_activity(mock_mongo_db, price=1000.0)
    # Activity 2: explicit cost override = 1500
    act_2 = await seed_activity(mock_mongo_db, price=2500.0)

    # Set hotel
    await client.put(f"/api/v1/trips/{trip_id}/hotel", json={"hotel_id": hotel_id}, headers=headers)

    # Set flights
    await client.put(
        f"/api/v1/trips/{trip_id}/flights",
        json={"outbound_flight_id": outbound_id, "return_flight_id": return_id},
        headers=headers,
    )

    # Add activities
    await client.put(
        f"/api/v1/trips/{trip_id}/activities",
        json={"action": "add", "day_number": 1, "activity_id": act_1},
        headers=headers,
    )
    res = await client.put(
        f"/api/v1/trips/{trip_id}/activities",
        json={"action": "add", "day_number": 2, "activity_id": act_2, "estimated_cost": 1500.0},
        headers=headers,
    )

    # Total expected:
    # Hotel: 12000
    # Flights: 8000 + 9000 = 17000
    # Activities: 2000 + 1500 = 3500
    # Total = 12000 + 17000 + 3500 = 32500.0
    data = res.json()
    assert data["estimated_total_cost"] == 32500.0

    # Retrieve again via GET to verify persistent recalculation
    get_res = await client.get(f"/api/v1/trips/{trip_id}/itinerary", headers=headers)
    assert get_res.status_code == 200
    assert get_res.json()["estimated_total_cost"] == 32500.0
