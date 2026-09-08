import pytest
from unittest.mock import patch, AsyncMock
import httpx


# ==============================================================================
# 1. DESTINATIONS TESTS
# ==============================================================================

@pytest.mark.asyncio
async def test_destination_crud_and_filters(client):
    # 1. Create destination
    payload = {
        "name": "Jaipur",
        "country": "India",
        "state": "Rajasthan",
        "city": "Jaipur",
        "description": "The Pink City",
        "tags": ["Heritage", "Culture"],
        "latitude": 26.9124,
        "longitude": 75.7873
    }
    res = await client.post("/api/v1/destinations", json=payload)
    assert res.status_code == 201
    dest = res.json()
    assert dest["name"] == "Jaipur"
    assert "id" in dest
    dest_id = dest["id"]

    # 2. Validation error on missing required country
    bad_res = await client.post("/api/v1/destinations", json={"name": "NoCountry"})
    assert bad_res.status_code == 422

    # 3. Get by ID
    get_res = await client.get(f"/api/v1/destinations/{dest_id}")
    assert get_res.status_code == 200
    assert get_res.json()["id"] == dest_id

    # 4. Invalid ObjectId format -> 400
    inv_res = await client.get("/api/v1/destinations/not-valid-id")
    assert inv_res.status_code == 400
    assert "Invalid destination ID" in inv_res.json()["detail"]

    # 5. Non-existent ObjectId -> 404
    nf_res = await client.get("/api/v1/destinations/60c72b2f9b1d8b2bad8d3b99")
    assert nf_res.status_code == 404

    # 6. List and search
    list_res = await client.get("/api/v1/destinations?search=Jaipur&country=India&page=1&limit=10")
    assert list_res.status_code == 200
    data = list_res.json()
    assert data["total"] == 1
    assert data["items"][0]["id"] == dest_id

    # Search non-matching keyword
    empty_res = await client.get("/api/v1/destinations?search=NonExistentPlace")
    assert empty_res.status_code == 200
    assert empty_res.json()["total"] == 0

    # 7. Update
    up_res = await client.put(f"/api/v1/destinations/{dest_id}", json={"description": "Updated Pink City"})
    assert up_res.status_code == 200
    assert up_res.json()["description"] == "Updated Pink City"

    # 8. Delete
    del_res = await client.delete(f"/api/v1/destinations/{dest_id}")
    assert del_res.status_code == 204

    # Verify deleted -> 404
    get_after = await client.get(f"/api/v1/destinations/{dest_id}")
    assert get_after.status_code == 404


# ==============================================================================
# 2. HOTELS TESTS
# ==============================================================================

@pytest.mark.asyncio
async def test_hotel_crud_and_filters(client):
    # 1. Create hotel
    payload = {
        "destination_id": "60c72b2f9b1d8b2bad8d3b71",
        "name": "Royal Palace Resort",
        "description": "5-star luxury",
        "address": "MI Road, Jaipur",
        "rating": 4.8,
        "price_per_night": 5000.0,
        "currency": "INR",
        "amenities": ["Pool", "WiFi"],
        "available_rooms": 10
    }
    res = await client.post("/api/v1/hotels", json=payload)
    assert res.status_code == 201
    hotel = res.json()
    hotel_id = hotel["id"]
    assert hotel["name"] == "Royal Palace Resort"

    # 2. Validation constraints (rating > 5 or price < 0)
    bad_rating = await client.post("/api/v1/hotels", json={**payload, "rating": 6.5})
    assert bad_rating.status_code == 422
    bad_price = await client.post("/api/v1/hotels", json={**payload, "price_per_night": -100})
    assert bad_price.status_code == 422

    # 3. Get by ID & Invalid ID
    get_res = await client.get(f"/api/v1/hotels/{hotel_id}")
    assert get_res.status_code == 200
    assert (await client.get("/api/v1/hotels/invalid-id")).status_code == 400
    assert (await client.get("/api/v1/hotels/60c72b2f9b1d8b2bad8d3b99")).status_code == 404

    # 4. List filters (destination_id, min_rating, price range)
    list_res = await client.get("/api/v1/hotels?destination_id=60c72b2f9b1d8b2bad8d3b71&min_rating=4.5&min_price=4000&max_price=6000")
    assert list_res.status_code == 200
    assert list_res.json()["total"] == 1

    # Price filter out of range
    out_res = await client.get("/api/v1/hotels?min_price=6000")
    assert out_res.status_code == 200
    assert out_res.json()["total"] == 0

    # 5. Update
    up_res = await client.put(f"/api/v1/hotels/{hotel_id}", json={"price_per_night": 4500.0})
    assert up_res.status_code == 200
    assert up_res.json()["price_per_night"] == 4500.0

    # 6. Delete
    del_res = await client.delete(f"/api/v1/hotels/{hotel_id}")
    assert del_res.status_code == 204
    assert (await client.get(f"/api/v1/hotels/{hotel_id}")).status_code == 404


# ==============================================================================
# 3. FLIGHTS TESTS
# ==============================================================================

@pytest.mark.asyncio
async def test_flight_crud_and_filters(client):
    payload = {
        "origin": "DEL",
        "destination": "JAI",
        "airline": "IndiGo",
        "flight_number": "6E-201",
        "departure_time": "2026-04-01T08:00:00Z",
        "arrival_time": "2026-04-01T09:00:00Z",
        "duration_minutes": 60,
        "price": 2500.0,
        "currency": "INR",
        "stops": 0,
        "available_seats": 30
    }
    # 1. Create flight
    res = await client.post("/api/v1/flights", json=payload)
    assert res.status_code == 201
    flight = res.json()
    flight_id = flight["id"]

    # 2. Validation error (duration <= 0)
    bad_dur = await client.post("/api/v1/flights", json={**payload, "duration_minutes": 0})
    assert bad_dur.status_code == 422

    # 3. Get flight
    assert (await client.get(f"/api/v1/flights/{flight_id}")).status_code == 200
    assert (await client.get("/api/v1/flights/invalid-id")).status_code == 400

    # 4. List filters
    list_res = await client.get("/api/v1/flights?origin=DEL&destination=JAI&airline=IndiGo&max_price=3000")
    assert list_res.status_code == 200
    assert list_res.json()["total"] == 1

    # 5. Update and Delete
    up_res = await client.put(f"/api/v1/flights/{flight_id}", json={"price": 2200.0})
    assert up_res.status_code == 200
    assert up_res.json()["price"] == 2200.0

    assert (await client.delete(f"/api/v1/flights/{flight_id}")).status_code == 204
    assert (await client.get(f"/api/v1/flights/{flight_id}")).status_code == 404


# ==============================================================================
# 4. ACTIVITIES TESTS
# ==============================================================================

@pytest.mark.asyncio
async def test_activity_crud_and_filters(client):
    payload = {
        "destination_id": "60c72b2f9b1d8b2bad8d3b71",
        "name": "Amber Fort Heritage Tour",
        "description": "Guided walking tour",
        "category": "Heritage",
        "duration_minutes": 120,
        "price": 400.0,
        "currency": "INR",
        "rating": 4.8,
        "location": "Jaipur"
    }
    # 1. Create activity
    res = await client.post("/api/v1/activities", json=payload)
    assert res.status_code == 201
    act = res.json()
    act_id = act["id"]

    # 2. Validation error (rating > 5)
    bad_rat = await client.post("/api/v1/activities", json={**payload, "rating": 5.5})
    assert bad_rat.status_code == 422

    # 3. Get and List
    assert (await client.get(f"/api/v1/activities/{act_id}")).status_code == 200
    list_res = await client.get("/api/v1/activities?destination_id=60c72b2f9b1d8b2bad8d3b71&category=Heritage&min_rating=4.0")
    assert list_res.status_code == 200
    assert list_res.json()["total"] == 1

    # 4. Update and Delete
    up_res = await client.put(f"/api/v1/activities/{act_id}", json={"price": 450.0})
    assert up_res.status_code == 200
    assert up_res.json()["price"] == 450.0

    assert (await client.delete(f"/api/v1/activities/{act_id}")).status_code == 204
    assert (await client.get(f"/api/v1/activities/{act_id}")).status_code == 404


# ==============================================================================
# 5. EXPENSES TESTS
# ==============================================================================

@pytest.mark.asyncio
async def test_expense_crud_and_summary(client):
    # 1. Create 2 expenses for trip_id=1
    exp1 = {
        "trip_id": 1,
        "category": "Food",
        "title": "Traditional Dinner",
        "amount": 1500.0,
        "currency": "INR",
        "expense_date": "2026-03-15",
        "notes": "Chokhi Dhani"
    }
    exp2 = {
        "trip_id": 1,
        "category": "Stay",
        "title": "Hotel Room Advance",
        "amount": 3500.0,
        "currency": "INR",
        "expense_date": "2026-03-15"
    }
    res1 = await client.post("/api/v1/expenses", json=exp1)
    res2 = await client.post("/api/v1/expenses", json=exp2)
    assert res1.status_code == 201
    assert res2.status_code == 201
    id1 = res1.json()["id"]
    id2 = res2.json()["id"]

    # 2. Validation error (negative amount)
    bad_amt = await client.post("/api/v1/expenses", json={**exp1, "amount": -50.0})
    assert bad_amt.status_code == 422

    # 3. List filtered by trip_id
    list_res = await client.get("/api/v1/expenses?trip_id=1")
    assert list_res.status_code == 200
    assert list_res.json()["total"] == 2

    # Filter by category
    food_res = await client.get("/api/v1/expenses?trip_id=1&category=Food")
    assert food_res.status_code == 200
    assert food_res.json()["total"] == 1

    # 4. Aggregated summary
    summary_res = await client.get("/api/v1/expenses/summary?trip_id=1")
    assert summary_res.status_code == 200
    summary = summary_res.json()
    assert summary["total_expenses"] == 2
    assert summary["total_amount"] == 5000.0
    assert summary["by_category"]["Food"] == 1500.0
    assert summary["by_category"]["Stay"] == 3500.0

    # 5. Update and Delete
    up_res = await client.put(f"/api/v1/expenses/{id1}", json={"amount": 1600.0})
    assert up_res.status_code == 200
    assert up_res.json()["amount"] == 1600.0

    assert (await client.delete(f"/api/v1/expenses/{id1}")).status_code == 204
    assert (await client.delete(f"/api/v1/expenses/{id2}")).status_code == 204
    assert (await client.get(f"/api/v1/expenses/{id1}")).status_code == 404


# ==============================================================================
# 6. WEATHER TESTS
# ==============================================================================

@pytest.mark.asyncio
async def test_weather_coordinates_validation(client):
    # Invalid latitude (> 90)
    res_lat = await client.get("/api/v1/weather?latitude=95.0&longitude=75.0")
    assert res_lat.status_code == 422

    # Invalid longitude (< -180)
    res_lon = await client.get("/api/v1/weather?latitude=25.0&longitude=-195.0")
    assert res_lon.status_code == 422


@pytest.mark.asyncio
async def test_weather_success_mock(client):
    mock_payload = {
        "current": {
            "temperature_2m": 27.4,
            "relative_humidity_2m": 45.0,
            "weather_code": 0,
            "wind_speed_10m": 11.2
        }
    }
    with patch("app.services.weather_service.httpx.AsyncClient") as mock_client_cls:
        mock_instance = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_instance
        mock_response = httpx.Response(
            status_code=200,
            json=mock_payload,
            request=httpx.Request("GET", "https://api.open-meteo.com/v1/forecast")
        )
        mock_instance.get.return_value = mock_response

        res = await client.get("/api/v1/weather?latitude=26.9124&longitude=75.7873")
        assert res.status_code == 200
        data = res.json()
        assert data["temperature"] == 27.4
        assert data["condition"] == "Clear sky"
        assert data["unit"] == "Celsius"


@pytest.mark.asyncio
async def test_weather_provider_failure(client):
    with patch("app.services.weather_service.httpx.AsyncClient") as mock_client_cls:
        mock_instance = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_instance
        mock_response = httpx.Response(
            status_code=500,
            text="Internal Server Error",
            request=httpx.Request("GET", "https://api.open-meteo.com/v1/forecast")
        )
        mock_instance.get.return_value = mock_response

        res = await client.get("/api/v1/weather?latitude=26.9124&longitude=75.7873")
        assert res.status_code == 503
        assert "Weather service provider error" in res.json()["detail"]


@pytest.mark.asyncio
async def test_weather_timeout_failure(client):
    with patch("app.services.weather_service.httpx.AsyncClient") as mock_client_cls:
        mock_instance = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_instance
        mock_instance.get.side_effect = httpx.TimeoutException("Connection timed out")

        res = await client.get("/api/v1/weather?latitude=26.9124&longitude=75.7873")
        assert res.status_code == 504
        assert "timed out" in res.json()["detail"]



# ==============================================================================
# 7. EXISTING AUTH, TRIP & HEALTH REGRESSION TESTS
# ==============================================================================

@pytest.mark.asyncio
async def test_existing_health_and_trips_intact(client):
    # Health endpoint
    h_res = await client.get("/api/v1/health")
    assert h_res.status_code == 200
    assert h_res.json()["status"] == "healthy"

    # Trip planning endpoint exists
    trip_payload = {
        "from_city": "Delhi",
        "destination": "Goa",
        "start_date": "2026-05-01",
        "end_date": "2026-05-05",
        "travellers": 2,
        "budget": 25000.0,
        "interests": ["Beach", "Food"]
    }
    trip_res = await client.post("/api/v1/trips/plan", json=trip_payload)
    assert trip_res.status_code == 200
    assert trip_res.json()["message"] == "Trip created successfully"

    # User registration and login endpoint exists
    user_res = await client.post(
        "/api/v1/users/",
        params={"name": "Test User", "email": "testuser_regression@odyssey.com", "password": "password123"}
    )
    # Can be 200 (created) or 400 (if already registered in local sqlite)
    assert user_res.status_code in [200, 400]

    login_res = await client.post(
        "/api/v1/users/login",
        params={"email": "testuser_regression@odyssey.com", "password": "password123"}
    )
    assert login_res.status_code == 200
    assert "access_token" in login_res.json()
