import pytest
from app.ai.assistant.intent import AssistantIntent
from app.ai.assistant.parser import parse_assistant_message
from app.core.database import SessionLocal
from app.models.trip import Trip
from tests.test_auth import register_and_login


async def seed_catalog(db):
    destination = await db["destinations"].insert_one({
        "name": "Goa",
        "country": "India",
    })
    destination_id = str(destination.inserted_id)
    await db["hotels"].insert_many([
        {
            "destination_id": destination_id,
            "name": "Budget Catalog Hotel",
            "price_per_night": 3000,
            "rating": 3.0,
            "currency": "INR",
        },
        {
            "destination_id": destination_id,
            "name": "Better Catalog Hotel",
            "price_per_night": 8000,
            "rating": 5.0,
            "currency": "INR",
        },
    ])
    await db["activities"].insert_many([
        {
            "destination_id": destination_id,
            "name": "Catalog Scuba Adventure",
            "category": "Adventure",
            "price": 1000,
            "rating": 4.9,
            "currency": "INR",
        },
        {
            "destination_id": destination_id,
            "name": "Catalog Hiking Adventure",
            "category": "Adventure",
            "price": 1200,
            "rating": 4.8,
            "currency": "INR",
        },
    ])


async def plan_for_chat(client, headers, interests=None):
    response = await client.post(
        "/api/v1/trips/plan",
        json={
            "from_city": "Delhi",
            "destination": "Goa",
            "start_date": "2026-05-01",
            "end_date": "2026-05-03",
            "travellers": 1,
            "budget": 20000,
            "interests": interests or [],
        },
        headers=headers,
    )
    assert response.status_code == 200
    return response.json()["trip_id"]


@pytest.mark.parametrize(
    ("message", "intent", "amount"),
    [
        ("make it cheaper", AssistantIntent.MAKE_CHEAPER, None),
        ("make it ₹10k cheaper", AssistantIntent.MAKE_CHEAPER, 10000),
        ("save 10,000", AssistantIntent.MAKE_CHEAPER, 10000),
        ("make it 10 thousand cheaper", AssistantIntent.MAKE_CHEAPER, 10000),
        ("upgrade my hotel", AssistantIntent.UPGRADE_HOTEL, None),
        ("how much budget is left?", AssistantIntent.REMAINING_BUDGET, None),
        ("add an adventure activity", AssistantIntent.ADD_ADVENTURE, None),
        ("avoid crowded places", AssistantIntent.AVOID_CROWDS, None),
        ("make day 2 relaxed", AssistantIntent.CHANGE_ITINERARY, None),
        ("why did you choose this hotel?", AssistantIntent.EXPLAIN_RECOMMENDATION, None),
    ],
)
def test_parser_supported_intents(message, intent, amount):
    result = parse_assistant_message(message)
    assert result.intent == intent
    assert result.amount == amount


def test_parser_rejects_invalid_explicit_saving_amount():
    result = parse_assistant_message("save abc")
    assert result.intent == AssistantIntent.MAKE_CHEAPER
    assert result.amount is None
    assert result.parse_error


def test_parser_unknown_command_is_non_mutating_intent():
    result = parse_assistant_message("tell me a travel joke")
    assert result.intent == AssistantIntent.UNKNOWN
    assert result.amount is None


@pytest.mark.asyncio
async def test_assistant_persists_cheaper_plan_and_next_command_uses_it(client, mock_mongo_db):
    await seed_catalog(mock_mongo_db)
    headers, _, _ = await register_and_login(client, "AssistantOwner")
    trip_id = await plan_for_chat(client, headers, interests=[])

    cheaper = await client.post(
        f"/api/v1/trips/{trip_id}/chat",
        json={"message": "make it ₹1k cheaper"},
        headers=headers,
    )
    assert cheaper.status_code == 200
    assert cheaper.json()["intent"] == "MAKE_CHEAPER"
    assert cheaper.json()["changed"] is True
    cheaper_cost = cheaper.json()["ai_plan"]["budget_plan"]["total_cost"]

    with SessionLocal() as db:
        persisted = db.query(Trip).filter(Trip.id == trip_id).one()
        assert persisted.ai_plan["budget_plan"]["total_cost"] == cheaper_cost

    upgrade = await client.post(
        f"/api/v1/trips/{trip_id}/chat",
        json={"message": "upgrade my hotel"},
        headers=headers,
    )
    assert upgrade.status_code == 200
    assert upgrade.json()["intent"] == "UPGRADE_HOTEL"
    assert upgrade.json()["changed"] is True
    assert upgrade.json()["ai_plan"]["budget_plan"]["total_cost"] <= 20000


@pytest.mark.asyncio
async def test_assistant_budget_failures_and_unknown_do_not_modify_plan(client, mock_mongo_db):
    await seed_catalog(mock_mongo_db)
    headers, _, _ = await register_and_login(client, "SafeAssistant")
    trip_id = await plan_for_chat(client, headers)

    before = await client.get(f"/api/v1/trips/{trip_id}", headers=headers)
    original_plan = before.json()["ai_plan"]

    impossible = await client.post(
        f"/api/v1/trips/{trip_id}/chat",
        json={"message": "make it ₹999k cheaper"},
        headers=headers,
    )
    assert impossible.status_code == 200
    assert impossible.json()["changed"] is False

    invalid = await client.post(
        f"/api/v1/trips/{trip_id}/chat",
        json={"message": "save abc"},
        headers=headers,
    )
    assert invalid.status_code == 200
    assert invalid.json()["changed"] is False

    unknown = await client.post(
        f"/api/v1/trips/{trip_id}/chat",
        json={"message": "tell me a joke"},
        headers=headers,
    )
    assert unknown.status_code == 200
    assert unknown.json()["intent"] == "UNKNOWN"
    assert unknown.json()["changed"] is False

    after = await client.get(f"/api/v1/trips/{trip_id}", headers=headers)
    assert after.json()["ai_plan"] == original_plan


@pytest.mark.asyncio
async def test_assistant_adds_catalog_adventure_and_updates_itinerary(client, mock_mongo_db):
    await seed_catalog(mock_mongo_db)
    headers, _, _ = await register_and_login(client, "AdventureAssistant")
    trip_id = await plan_for_chat(client, headers, interests=[])
    destination = await mock_mongo_db["destinations"].find_one({"name": "Goa"})
    await mock_mongo_db["activities"].insert_one({
        "destination_id": str(destination["_id"]),
        "name": "Catalog Kayaking Adventure",
        "category": "Adventure",
        "price": 1200,
        "rating": 4.7,
        "currency": "INR",
    })

    response = await client.post(
        f"/api/v1/trips/{trip_id}/chat",
        json={"message": "add an adventure activity"},
        headers=headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["changed"] is True
    selected_names = {
        option["name"]
        for option in body["ai_plan"]["budget_plan"]["selected_options"]
    }
    assert "Catalog Kayaking Adventure" in selected_names
    assert body["ai_plan"]["budget_plan"]["total_cost"] <= 20000


@pytest.mark.asyncio
async def test_assistant_rejects_adventure_that_exceeds_budget(client, mock_mongo_db):
    await seed_catalog(mock_mongo_db)
    headers, _, _ = await register_and_login(client, "BudgetAdventureAssistant")
    trip_id = await plan_for_chat(client, headers, interests=[])

    destination = await mock_mongo_db["destinations"].find_one({"name": "Goa"})
    await mock_mongo_db["activities"].insert_one({
        "destination_id": str(destination["_id"]),
        "name": "Expensive Adventure",
        "category": "Adventure",
        "price": 100000,
        "rating": 5,
        "currency": "INR",
    })

    before = await client.get(f"/api/v1/trips/{trip_id}", headers=headers)
    response = await client.post(
        f"/api/v1/trips/{trip_id}/chat",
        json={"message": "add an adventure activity"},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["changed"] is False
    after = await client.get(f"/api/v1/trips/{trip_id}", headers=headers)
    assert after.json()["ai_plan"] == before.json()["ai_plan"]


@pytest.mark.asyncio
async def test_assistant_stores_crowd_preference_and_local_itinerary_change(client, mock_mongo_db):
    await seed_catalog(mock_mongo_db)
    headers, _, _ = await register_and_login(client, "PreferenceAssistant")
    trip_id = await plan_for_chat(client, headers)

    crowd = await client.post(
        f"/api/v1/trips/{trip_id}/chat",
        json={"message": "I don't want crowded places"},
        headers=headers,
    )
    assert crowd.status_code == 200
    assert crowd.json()["changed"] is True
    assert "unavailable" in crowd.json()["message"].lower()

    itinerary = await client.post(
        f"/api/v1/trips/{trip_id}/chat",
        json={"message": "make day 2 relaxed"},
        headers=headers,
    )
    assert itinerary.status_code == 200
    assert itinerary.json()["changed"] is True
    day_two = next(
        day for day in itinerary.json()["ai_plan"]["itinerary"]
        if day["day"] == 2
    )
    assert day_two["activities"] == []
    assert day_two["note"] == "Relaxed / Free Day"