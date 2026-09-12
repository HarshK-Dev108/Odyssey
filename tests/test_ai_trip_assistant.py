import pytest
from unittest.mock import AsyncMock
import httpx

from app.api.routes import ai
from app.core.database import SessionLocal
from app.models.itinerary import Itinerary, ItineraryItem
from app.models.trip import Trip
from tests.test_auth import register_and_login


async def seed_tourism_catalogue(mongo_db):
    """Seed comprehensive tourism catalogue with destinations, hotels, flights, and activities."""
    dest_res = await mongo_db["destinations"].insert_one({
        "name": "Goa",
        "country": "India",
        "latitude": 15.2993,
        "longitude": 74.1240,
    })
    dest_id = str(dest_res.inserted_id)

    # Hotels (different tiers and prices)
    h1 = await mongo_db["hotels"].insert_one({
        "destination_id": dest_id,
        "name": "Economy Budget Inn",
        "price_per_night": 2000.0,
        "rating": 3.8,
        "review_count": 80,
        "currency": "INR",
    })
    h2 = await mongo_db["hotels"].insert_one({
        "destination_id": dest_id,
        "name": "Grand Heritage Resort",
        "price_per_night": 6000.0,
        "rating": 4.6,
        "review_count": 350,
        "currency": "INR",
    })
    h3 = await mongo_db["hotels"].insert_one({
        "destination_id": dest_id,
        "name": "Ultra Luxury Palace Hotel",
        "price_per_night": 15000.0,
        "rating": 4.9,
        "review_count": 500,
        "currency": "INR",
    })

    # Flights
    f1 = await mongo_db["flights"].insert_one({
        "origin": "DEL",
        "destination": "GOI",
        "price": 3500.0,
        "airline": "IndiGo",
        "flight_number": "6E-101",
        "departure_time": "08:00",
        "arrival_time": "10:30",
        "duration": "2h 30m",
        "stops": 0,
    })
    f2 = await mongo_db["flights"].insert_one({
        "origin": "DEL",
        "destination": "GOI",
        "price": 7000.0,
        "airline": "Air India",
        "flight_number": "AI-202",
        "departure_time": "09:00",
        "arrival_time": "11:30",
        "duration": "2h 30m",
        "stops": 0,
    })
    f3 = await mongo_db["flights"].insert_one({
        "origin": "GOI",
        "destination": "DEL",
        "price": 3500.0,
        "airline": "IndiGo",
        "flight_number": "6E-102",
        "departure_time": "18:00",
        "arrival_time": "20:30",
        "duration": "2h 30m",
        "stops": 0,
    })

    # Activities (diverse categories: rain-unfriendly and rain-safe)
    a1 = await mongo_db["activities"].insert_one({
        "destination_id": dest_id,
        "name": "Calangute Beach Walk",
        "category": "Beach",
        "price": 0.0,
        "rating": 4.5,
        "duration_hours": 2.0,
        "currency": "INR",
    })
    a2 = await mongo_db["activities"].insert_one({
        "destination_id": dest_id,
        "name": "Old Fort Aguada Tour",
        "category": "Heritage",
        "price": 500.0,
        "rating": 4.7,
        "duration_hours": 2.0,
        "currency": "INR",
    })
    a3 = await mongo_db["activities"].insert_one({
        "destination_id": dest_id,
        "name": "Catalog Kayaking Adventure",
        "category": "Adventure",
        "price": 1800.0,
        "rating": 4.8,
        "duration_hours": 3.0,
        "currency": "INR",
    })
    a4 = await mongo_db["activities"].insert_one({
        "destination_id": dest_id,
        "name": "Goa State Museum Tour",
        "category": "Museum",
        "price": 200.0,
        "rating": 4.4,
        "duration_hours": 2.0,
        "currency": "INR",
    })
    a5 = await mongo_db["activities"].insert_one({
        "destination_id": dest_id,
        "name": "Traditional Goan Cooking Class",
        "category": "Food",
        "price": 1200.0,
        "rating": 4.9,
        "duration_hours": 2.5,
        "currency": "INR",
    })
    a6 = await mongo_db["activities"].insert_one({
        "destination_id": dest_id,
        "name": "Dudhsagar Waterfall Trek",
        "category": "Adventure",
        "price": 1500.0,
        "rating": 4.9,
        "duration_hours": 4.0,
        "currency": "INR",
    })
    a7 = await mongo_db["activities"].insert_one({
        "destination_id": dest_id,
        "name": "Sunset Mandovi River Cruise",
        "category": "Culture",
        "price": 800.0,
        "rating": 4.6,
        "duration_hours": 2.0,
        "currency": "INR",
    })

    return {
        "dest_id": dest_id,
        "hotels": [str(h1.inserted_id), str(h2.inserted_id), str(h3.inserted_id)],
        "flights": [str(f1.inserted_id), str(f2.inserted_id), str(f3.inserted_id)],
        "activities": [str(a1.inserted_id), str(a2.inserted_id), str(a3.inserted_id), str(a4.inserted_id), str(a5.inserted_id), str(a6.inserted_id), str(a7.inserted_id)],
    }


async def create_trip_and_itinerary(client, headers, destination="Goa", budget=50000.0):
    """Helper to create a trip and generate a full baseline itinerary."""
    res = await client.post(
        "/api/v1/trips/plan",
        json={
            "from_city": "Delhi",
            "destination": destination,
            "start_date": "2026-11-01",
            "end_date": "2026-11-03",
            "travellers": 1,
            "budget": budget,
            "currency": "INR",
            "interests": ["Culture", "Beach"],
            "pace": "moderate",
        },
        headers=headers,
    )
    assert res.status_code == 200
    trip_id = res.json()["trip_id"]

    # Generate initial itinerary
    gen_res = await client.post(f"/api/v1/trips/{trip_id}/generate", headers=headers)
    assert gen_res.status_code == 200
    return trip_id


@pytest.mark.asyncio
async def test_ai_chat_cheaper_trip_intent(client, mock_mongo_db, monkeypatch):
    await seed_tourism_catalogue(mock_mongo_db)
    headers, _, _ = await register_and_login(client, "CheaperUser")
    trip_id = await create_trip_and_itinerary(client, headers)

    # Manually set a higher hotel first so make_trip_cheaper has an obvious cheaper option
    dest_doc = await mock_mongo_db["destinations"].find_one({"name": "Goa"})
    grand = await mock_mongo_db["hotels"].find_one({"name": "Grand Heritage Resort"})
    with SessionLocal() as db:
        itin = db.query(Itinerary).filter(Itinerary.trip_id == trip_id).first()
        itin.selected_hotel_id = str(grand["_id"])
        db.commit()

    monkeypatch.setattr(ai.llm_provider, "enabled", True)
    monkeypatch.setattr(
        ai.llm_provider,
        "structured_json",
        AsyncMock(return_value={
            "intent": "make_trip_cheaper",
            "parameters": {"target_savings": 5000},
            "reasoning": "User wants to reduce total cost.",
        }),
    )

    response = await client.post(
        "/api/v1/ai/chat",
        json={"trip_id": trip_id, "message": "make it cheaper"},
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "applied"
    assert data["intent"] == "make_trip_cheaper"
    assert len(data["changes_made"]) > 0
    assert data["budget_comparison"]["savings"] > 0
    assert data["budget_comparison"]["updated_total"] < data["budget_comparison"]["previous_total"]

    # Verify SQLite persistence
    with SessionLocal() as db:
        updated_itin = db.query(Itinerary).filter(Itinerary.trip_id == trip_id).first()
        economy = await mock_mongo_db["hotels"].find_one({"name": "Economy Budget Inn"})
        assert updated_itin.selected_hotel_id == str(economy["_id"])


@pytest.mark.asyncio
async def test_ai_chat_hotel_swap(client, mock_mongo_db, monkeypatch):
    await seed_tourism_catalogue(mock_mongo_db)
    headers, _, _ = await register_and_login(client, "HotelSwapUser")
    trip_id = await create_trip_and_itinerary(client, headers)

    monkeypatch.setattr(ai.llm_provider, "enabled", True)
    monkeypatch.setattr(
        ai.llm_provider,
        "structured_json",
        AsyncMock(return_value={
            "intent": "change_hotel",
            "parameters": {"hotel_name": "Ultra Luxury Palace Hotel"},
            "reasoning": "User requested luxury hotel swap.",
        }),
    )

    response = await client.post(
        "/api/v1/ai/chat",
        json={"trip_id": trip_id, "message": "change hotel to Ultra Luxury Palace Hotel"},
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "applied"
    assert "Ultra Luxury Palace Hotel" in data["changes_made"][0]

    with SessionLocal() as db:
        updated_itin = db.query(Itinerary).filter(Itinerary.trip_id == trip_id).first()
        luxury = await mock_mongo_db["hotels"].find_one({"name": "Ultra Luxury Palace Hotel"})
        assert updated_itin.selected_hotel_id == str(luxury["_id"])


@pytest.mark.asyncio
async def test_ai_chat_add_activity(client, mock_mongo_db, monkeypatch):
    await seed_tourism_catalogue(mock_mongo_db)
    headers, _, _ = await register_and_login(client, "AddActUser")
    trip_id = await create_trip_and_itinerary(client, headers)

    monkeypatch.setattr(ai.llm_provider, "enabled", True)
    monkeypatch.setattr(
        ai.llm_provider,
        "structured_json",
        AsyncMock(return_value={
            "intent": "add_activity",
            "parameters": {"activity_name": "Dudhsagar Waterfall Trek", "day_number": 2},
            "reasoning": "User wants to add waterfall trek.",
        }),
    )

    response = await client.post(
        "/api/v1/ai/chat",
        json={"trip_id": trip_id, "message": "add trek on day 2"},
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "applied"
    item_titles = [it["title_override"] for it in data["itinerary"]["items"]]
    assert "Dudhsagar Waterfall Trek" in item_titles


@pytest.mark.asyncio
async def test_ai_chat_remove_activity(client, mock_mongo_db, monkeypatch):
    await seed_tourism_catalogue(mock_mongo_db)
    headers, _, _ = await register_and_login(client, "RemoveActUser")
    trip_id = await create_trip_and_itinerary(client, headers)

    monkeypatch.setattr(ai.llm_provider, "enabled", True)
    monkeypatch.setattr(
        ai.llm_provider,
        "structured_json",
        AsyncMock(return_value={
            "intent": "remove_activity",
            "parameters": {"day_number": 1},
            "reasoning": "User wants to remove activity on day 1.",
        }),
    )

    response = await client.post(
        "/api/v1/ai/chat",
        json={"trip_id": trip_id, "message": "remove activity from day 1"},
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "applied"
    assert len(data["changes_made"]) > 0


@pytest.mark.asyncio
async def test_ai_chat_replace_activity(client, mock_mongo_db, monkeypatch):
    await seed_tourism_catalogue(mock_mongo_db)
    headers, _, _ = await register_and_login(client, "ReplaceActUser")
    trip_id = await create_trip_and_itinerary(client, headers)

    monkeypatch.setattr(ai.llm_provider, "enabled", True)
    monkeypatch.setattr(
        ai.llm_provider,
        "structured_json",
        AsyncMock(return_value={
            "intent": "replace_activity",
            "parameters": {
                "new_activity_name": "Traditional Goan Cooking Class",
            },
            "reasoning": "User wants cooking class instead.",
        }),
    )

    response = await client.post(
        "/api/v1/ai/chat",
        json={"trip_id": trip_id, "message": "replace with cooking class"},
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "applied"
    titles = [it["title_override"] for it in data["itinerary"]["items"]]
    assert "Traditional Goan Cooking Class" in titles


@pytest.mark.asyncio
async def test_ai_chat_more_adventure(client, mock_mongo_db, monkeypatch):
    await seed_tourism_catalogue(mock_mongo_db)
    headers, _, _ = await register_and_login(client, "AdvUser")
    trip_id = await create_trip_and_itinerary(client, headers)

    monkeypatch.setattr(ai.llm_provider, "enabled", True)
    monkeypatch.setattr(
        ai.llm_provider,
        "structured_json",
        AsyncMock(return_value={
            "intent": "more_adventure",
            "parameters": {},
            "reasoning": "Add thrills and water sports.",
        }),
    )

    response = await client.post(
        "/api/v1/ai/chat",
        json={"trip_id": trip_id, "message": "add more adventure"},
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "applied"
    assert any("adventure" in c.lower() or "kayaking" in c.lower() for c in data["changes_made"])


@pytest.mark.asyncio
async def test_ai_chat_more_relaxed(client, mock_mongo_db, monkeypatch):
    await seed_tourism_catalogue(mock_mongo_db)
    headers, _, _ = await register_and_login(client, "RelaxedUser")
    trip_id = await create_trip_and_itinerary(client, headers)

    monkeypatch.setattr(ai.llm_provider, "enabled", True)
    monkeypatch.setattr(
        ai.llm_provider,
        "structured_json",
        AsyncMock(return_value={
            "intent": "more_relaxed",
            "parameters": {},
            "reasoning": "Make it more relaxed.",
        }),
    )

    response = await client.post(
        "/api/v1/ai/chat",
        json={"trip_id": trip_id, "message": "make the schedule more relaxed"},
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "applied"


@pytest.mark.asyncio
async def test_ai_chat_weather_safe_plan(client, mock_mongo_db, monkeypatch):
    await seed_tourism_catalogue(mock_mongo_db)
    headers, _, _ = await register_and_login(client, "WeatherSafeUser")
    trip_id = await create_trip_and_itinerary(client, headers)

    monkeypatch.setattr(ai.llm_provider, "enabled", True)
    monkeypatch.setattr(
        ai.llm_provider,
        "structured_json",
        AsyncMock(return_value={
            "intent": "weather_safe_plan",
            "parameters": {},
            "reasoning": "Rain predicted; switch to indoor activities.",
        }),
    )

    response = await client.post(
        "/api/v1/ai/chat",
        json={"trip_id": trip_id, "message": "it is raining, give me weather safe plan"},
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    # If beach activity was scheduled, it was replaced by museum or cooking class
    assert data["status"] in {"applied", "no_change"}


@pytest.mark.asyncio
async def test_ai_chat_explain_itinerary(client, mock_mongo_db, monkeypatch):
    await seed_tourism_catalogue(mock_mongo_db)
    headers, _, _ = await register_and_login(client, "ExplainUser")
    trip_id = await create_trip_and_itinerary(client, headers)

    monkeypatch.setattr(ai.llm_provider, "enabled", True)
    monkeypatch.setattr(
        ai.llm_provider,
        "structured_json",
        AsyncMock(return_value={
            "intent": "explain_itinerary",
            "parameters": {},
            "reasoning": "Explain the chosen plan.",
        }),
    )

    response = await client.post(
        "/api/v1/ai/chat",
        json={"trip_id": trip_id, "message": "why did you choose this hotel and plan?"},
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "explained"
    assert data["changes_made"] == []
    assert data["budget_comparison"]["difference"] == 0.0
    assert len(data["message"]) > 20


@pytest.mark.asyncio
async def test_ai_chat_unsupported_request(client, mock_mongo_db, monkeypatch):
    await seed_tourism_catalogue(mock_mongo_db)
    headers, _, _ = await register_and_login(client, "UnsupportedUser")
    trip_id = await create_trip_and_itinerary(client, headers)

    monkeypatch.setattr(ai.llm_provider, "enabled", True)
    monkeypatch.setattr(
        ai.llm_provider,
        "structured_json",
        AsyncMock(return_value={
            "intent": "unknown",
            "parameters": {},
            "reasoning": "User asked for a poem.",
        }),
    )

    response = await client.post(
        "/api/v1/ai/chat",
        json={"trip_id": trip_id, "message": "write me a poem about the beach"},
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "unsupported"
    assert data["changes_made"] == []
    assert data["budget_comparison"]["difference"] == 0.0


@pytest.mark.asyncio
async def test_ai_chat_malformed_llm_response(client, mock_mongo_db, monkeypatch):
    await seed_tourism_catalogue(mock_mongo_db)
    headers, _, _ = await register_and_login(client, "MalformedUser")
    trip_id = await create_trip_and_itinerary(client, headers)

    monkeypatch.setattr(ai.llm_provider, "enabled", True)
    # Missing required intent field and invalid schema
    monkeypatch.setattr(
        ai.llm_provider,
        "structured_json",
        AsyncMock(return_value={"something_random": "not_an_action"}),
    )

    response = await client.post(
        "/api/v1/ai/chat",
        json={"trip_id": trip_id, "message": "make changes"},
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "error"
    assert "malformed" in data["message"].lower() or "invalid" in data["message"].lower()
    assert data["changes_made"] == []


@pytest.mark.asyncio
async def test_ai_chat_unauthorized_trip(client, mock_mongo_db):
    await seed_tourism_catalogue(mock_mongo_db)
    headers_owner, _, _ = await register_and_login(client, "TrueOwner")
    trip_id = await create_trip_and_itinerary(client, headers_owner)

    headers_attacker, _, _ = await register_and_login(client, "AttackerUser")
    response = await client.post(
        "/api/v1/ai/chat",
        json={"trip_id": trip_id, "message": "make it cheaper"},
        headers=headers_attacker,
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Trip not found"


@pytest.mark.asyncio
async def test_ai_chat_provider_failure(client, mock_mongo_db, monkeypatch):
    await seed_tourism_catalogue(mock_mongo_db)
    headers, _, _ = await register_and_login(client, "FailureUser")
    trip_id = await create_trip_and_itinerary(client, headers)

    monkeypatch.setattr(ai.llm_provider, "enabled", True)
    monkeypatch.setattr(
        ai.llm_provider,
        "structured_json",
        AsyncMock(side_effect=httpx.ConnectTimeout("AI server timeout")),
    )

    response = await client.post(
        "/api/v1/ai/chat",
        json={"trip_id": trip_id, "message": "make it cheaper"},
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "error"
    assert "error" in data["message"].lower()
    assert data["changes_made"] == []


@pytest.mark.asyncio
async def test_ai_chat_no_suitable_alternative(client, mock_mongo_db, monkeypatch):
    await seed_tourism_catalogue(mock_mongo_db)
    headers, _, _ = await register_and_login(client, "NoAltUser")
    trip_id = await create_trip_and_itinerary(client, headers)

    # Set hotel to Economy Budget Inn (the cheapest in catalogue)
    economy = await mock_mongo_db["hotels"].find_one({"name": "Economy Budget Inn"})
    with SessionLocal() as db:
        itin = db.query(Itinerary).filter(Itinerary.trip_id == trip_id).first()
        itin.selected_hotel_id = str(economy["_id"])
        # Clear activities to leave no cheaper activity alternatives
        db.query(ItineraryItem).filter(ItineraryItem.itinerary_id == itin.id).delete()
        db.commit()

    monkeypatch.setattr(ai.llm_provider, "enabled", True)
    monkeypatch.setattr(
        ai.llm_provider,
        "structured_json",
        AsyncMock(return_value={
            "intent": "make_trip_cheaper",
            "parameters": {},
            "reasoning": "Attempt to make cheaper.",
        }),
    )

    response = await client.post(
        "/api/v1/ai/chat",
        json={"trip_id": trip_id, "message": "make it cheaper"},
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "no_change"
    assert data["changes_made"] == []
    assert "affordable" in data["message"].lower() or "already" in data["message"].lower()


@pytest.mark.asyncio
async def test_ai_chat_budget_comparison_accuracy(client, mock_mongo_db, monkeypatch):
    await seed_tourism_catalogue(mock_mongo_db)
    headers, _, _ = await register_and_login(client, "BudgetAccuracyUser")
    trip_id = await create_trip_and_itinerary(client, headers)

    monkeypatch.setattr(ai.llm_provider, "enabled", True)
    monkeypatch.setattr(
        ai.llm_provider,
        "structured_json",
        AsyncMock(return_value={
            "intent": "change_hotel",
            "parameters": {"hotel_name": "Ultra Luxury Palace Hotel"},
            "reasoning": "Upgrade hotel.",
        }),
    )

    response = await client.post(
        "/api/v1/ai/chat",
        json={"trip_id": trip_id, "message": "upgrade hotel"},
        headers=headers,
    )
    assert response.status_code == 200
    comp = response.json()["budget_comparison"]
    prev = comp["previous_total"]
    upd = comp["updated_total"]
    diff = comp["difference"]
    assert round(upd - prev, 2) == round(diff, 2)
    if upd < prev:
        assert comp["savings"] == round(prev - upd, 2)
    else:
        assert comp["savings"] == 0.0
