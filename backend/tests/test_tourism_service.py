import pytest
from mongomock_motor import AsyncMongoMockClient

from app.ai.agent.travel_agent import TravelAgent
from app.ai.itinerary.itinerary_generator import ItineraryGenerator
from app.ai.optimizer.budget_optimizer import BudgetOptimizer
from app.ai.recommendation.recommender import TravelRecommender
from app.services.tourism_service import get_tourism_options


@pytest.fixture
def tourism_components():
    return TravelAgent(
        recommender=TravelRecommender(),
        budget_optimizer=BudgetOptimizer(),
        itinerary_generator=ItineraryGenerator(),
    )


@pytest.fixture
def mock_db():
    client = AsyncMongoMockClient()
    return client["tourism_service_test"]


async def seed_destination(db, name="Goa"):
    result = await db["destinations"].insert_one({"name": name, "country": "India"})
    return str(result.inserted_id)


@pytest.mark.asyncio
async def test_normalizes_mongodb_options_and_hotel_nights(mock_db):
    destination_id = await seed_destination(mock_db)
    await mock_db["hotels"].insert_one({
        "destination_id": destination_id,
        "name": "Catalog Beach Hotel",
        "price_per_night": 4000,
        "rating": 4.5,
        "currency": "INR",
    })
    await mock_db["activities"].insert_one({
        "destination_id": destination_id,
        "name": "Scuba Adventure",
        "category": "Adventure",
        "price": 1500,
        "rating": 4.8,
        "currency": "INR",
        "duration_minutes": 120,
    })
    await mock_db["flights"].insert_one({
        "origin": "Delhi",
        "destination": "Goa",
        "flight_number": "AI-101",
        "airline": "Air India",
        "price": 5000,
        "currency": "INR",
    })

    options = await get_tourism_options(
        db=mock_db,
        destination="goa",
        from_city="delhi",
        nights=3,
        travellers=2,
    )

    by_type = {option["type"]: option for option in options}
    assert by_type["hotel"]["price"] == 12000
    assert by_type["hotel"]["unit_price"] == 4000
    assert by_type["activity"]["price"] == 3000
    assert by_type["activity"]["interests"] == ["adventure"]
    assert by_type["flight"]["price"] == 10000
    assert by_type["flight"]["unit_price"] == 5000


@pytest.mark.asyncio
async def test_mongodb_options_reach_existing_travel_agent(mock_db, tourism_components):
    destination_id = await seed_destination(mock_db)
    await mock_db["activities"].insert_one({
        "destination_id": destination_id,
        "name": "Catalog Adventure",
        "category": "Adventure",
        "price": 1000,
        "rating": 5,
        "currency": "INR",
    })

    options = await get_tourism_options(
        db=mock_db,
        destination="Goa",
        from_city="Delhi",
        nights=2,
        travellers=1,
    )
    plan = tourism_components.plan_trip(
        options=options,
        interests=["adventure"],
        budget=5000,
        hotel_rating=3,
        days=2,
    )

    assert plan["budget_plan"]["selected_options"][0]["name"] == "Catalog Adventure"


@pytest.mark.asyncio
async def test_trip_planning_route_uses_mongodb_catalog(
    client,
    mock_mongo_db,
    auth_headers,
):
    destination_id = await seed_destination(mock_mongo_db)
    await mock_mongo_db["activities"].insert_one({
        "destination_id": destination_id,
        "name": "Route Catalog Adventure",
        "category": "Adventure",
        "price": 1000,
        "rating": 5,
        "currency": "INR",
    })

    response = await client.post(
        "/api/v1/trips/plan",
        json={
            "from_city": "Delhi",
            "destination": "Goa",
            "start_date": "2026-05-01",
            "end_date": "2026-05-03",
            "travellers": 1,
            "budget": 5000,
            "interests": ["adventure"],
        },
        headers=auth_headers,
    )

    assert response.status_code == 200
    selected = response.json()["ai_plan"]["budget_plan"]["selected_options"]
    assert selected[0]["name"] == "Route Catalog Adventure"
    assert selected[0]["source"] == "mongodb"


@pytest.mark.asyncio
async def test_static_catalog_is_fallback_when_mongodb_has_no_usable_data(mock_db):
    options = await get_tourism_options(
        db=mock_db,
        destination="Thailand",
        from_city="Delhi",
        nights=2,
        travellers=2,
    )

    assert options
    assert all(option.get("source") != "mongodb" for option in options)
    assert any(option["name"] == "Budget City Hotel" for option in options)


@pytest.mark.asyncio
async def test_static_catalog_is_fallback_when_mongodb_lookup_fails(monkeypatch, mock_db):
    async def fail_find_one(*args, **kwargs):
        raise RuntimeError("MongoDB unavailable")

    monkeypatch.setattr(mock_db["destinations"], "find_one", fail_find_one)

    options = await get_tourism_options(
        db=mock_db,
        destination="Thailand",
        from_city="Delhi",
        nights=2,
        travellers=2,
    )

    assert any(option["name"] == "Budget City Hotel" for option in options)