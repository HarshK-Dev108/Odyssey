from uuid import uuid4
import pytest

from app.core.database import SessionLocal
from app.models.trip import Trip
from app.models.user import User


async def create_user_and_headers(client, name: str):
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


def sample_trip_payload(**overrides):
    payload = {
        "from_city": "Delhi",
        "destination": "Goa",
        "start_date": "2026-06-01",
        "end_date": "2026-06-05",
        "travellers": 2,
        "budget": 10000.0,
        "currency": "INR",
        "interests": ["Beach", "Culture"],
        "hotel_rating": 4,
        "pace": "moderate",
        "avoid_crowds": False,
    }
    payload.update(overrides)
    return payload


# 1. Unauthenticated trip creation rejected
@pytest.mark.asyncio
async def test_unauthenticated_trip_creation_rejected(client):
    res = await client.post("/api/v1/trips/plan", json=sample_trip_payload())
    assert res.status_code == 401


# 2. Authenticated user can create trip
@pytest.mark.asyncio
async def test_authenticated_user_can_create_trip(client):
    headers, user_id = await create_user_and_headers(client, "Creator")
    res = await client.post("/api/v1/trips/plan", json=sample_trip_payload(), headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "trip_id" in data
    assert data["message"] == "AI travel plan created successfully"


# 3. Created trip belongs to logged-in user (ignoring client-provided user_id)
@pytest.mark.asyncio
async def test_created_trip_belongs_to_logged_in_user(client):
    headers, user_id = await create_user_and_headers(client, "OwnerCheck")
    # Even if client maliciously sends user_id: 99999
    spoofed_payload = sample_trip_payload(user_id=99999)
    res = await client.post("/api/v1/trips/plan", json=spoofed_payload, headers=headers)
    assert res.status_code == 200
    trip_id = res.json()["trip_id"]

    with SessionLocal() as db:
        trip = db.query(Trip).filter(Trip.id == trip_id).first()
        assert trip is not None
        assert trip.user_id == user_id
        # Also check SQLAlchemy relationships: owner and user alias
        assert trip.owner.id == user_id
        assert trip.user.id == user_id
        owner_user = db.query(User).filter(User.id == user_id).first()
        assert any(t.id == trip_id for t in owner_user.trips)


# 4. User can list their own trips
@pytest.mark.asyncio
async def test_user_can_list_their_own_trips(client):
    headers, user_id = await create_user_and_headers(client, "Lister")
    res1 = await client.post("/api/v1/trips/plan", json=sample_trip_payload(destination="Goa"), headers=headers)
    assert res1.status_code == 200
    res2 = await client.post("/api/v1/trips/plan", json=sample_trip_payload(destination="Kerala"), headers=headers)
    assert res2.status_code == 200

    list_res = await client.get("/api/v1/trips/", headers=headers)
    assert list_res.status_code == 200
    trips = list_res.json()
    assert isinstance(trips, list)
    trip_ids = [t["trip_id"] for t in trips]
    assert res1.json()["trip_id"] in trip_ids
    assert res2.json()["trip_id"] in trip_ids
    assert all(t["user_id"] == user_id for t in trips)


# 5. User A cannot retrieve User B's trip
@pytest.mark.asyncio
async def test_user_a_cannot_retrieve_user_b_trip(client):
    headers_a, _ = await create_user_and_headers(client, "UserA")
    headers_b, _ = await create_user_and_headers(client, "UserB")

    create_res = await client.post("/api/v1/trips/plan", json=sample_trip_payload(), headers=headers_a)
    assert create_res.status_code == 200
    trip_id_a = create_res.json()["trip_id"]

    # User B tries to get User A's trip
    get_res = await client.get(f"/api/v1/trips/{trip_id_a}", headers=headers_b)
    assert get_res.status_code == 404
    assert get_res.json()["detail"] == "Trip not found"


# 6. User A cannot update User B's trip
@pytest.mark.asyncio
async def test_user_a_cannot_update_user_b_trip(client):
    headers_a, _ = await create_user_and_headers(client, "OwnerA")
    headers_b, _ = await create_user_and_headers(client, "AttackerB")

    create_res = await client.post("/api/v1/trips/plan", json=sample_trip_payload(destination="Goa"), headers=headers_a)
    trip_id_a = create_res.json()["trip_id"]

    # User B tries to update User A's trip
    update_res = await client.put(
        f"/api/v1/trips/{trip_id_a}",
        json={"destination": "HackedCity", "budget": 1.0},
        headers=headers_b,
    )
    assert update_res.status_code == 404

    # Verify original trip remained unchanged in database
    with SessionLocal() as db:
        trip = db.query(Trip).filter(Trip.id == trip_id_a).first()
        assert trip.destination == "Goa"


# 7. User A cannot delete User B's trip
@pytest.mark.asyncio
async def test_user_a_cannot_delete_user_b_trip(client):
    headers_a, _ = await create_user_and_headers(client, "SafeUserA")
    headers_b, _ = await create_user_and_headers(client, "BadUserB")

    create_res = await client.post("/api/v1/trips/plan", json=sample_trip_payload(), headers=headers_a)
    trip_id_a = create_res.json()["trip_id"]

    # User B tries to delete User A's trip
    del_res = await client.delete(f"/api/v1/trips/{trip_id_a}", headers=headers_b)
    assert del_res.status_code == 404

    # Verify trip still exists in database
    with SessionLocal() as db:
        trip = db.query(Trip).filter(Trip.id == trip_id_a).first()
        assert trip is not None


# 8. Authenticated user can update their own trip
@pytest.mark.asyncio
async def test_authenticated_user_can_update_their_own_trip(client):
    headers, user_id = await create_user_and_headers(client, "TripUpdater")
    create_res = await client.post(
        "/api/v1/trips/plan",
        json=sample_trip_payload(destination="OriginalGoa", budget=5000.0),
        headers=headers,
    )
    trip_id = create_res.json()["trip_id"]

    update_res = await client.put(
        f"/api/v1/trips/{trip_id}",
        json={"destination": "UpdatedGoa", "budget": 7500.0},
        headers=headers,
    )
    assert update_res.status_code == 200
    data = update_res.json()
    assert data["destination"] == "UpdatedGoa"
    assert data["budget"] == 7500.0
    assert data["trip_id"] == trip_id

    # Verify in DB
    with SessionLocal() as db:
        trip = db.query(Trip).filter(Trip.id == trip_id).first()
        assert trip.destination == "UpdatedGoa"
        assert trip.budget == 7500.0


# 9. Authenticated user can delete their own trip
@pytest.mark.asyncio
async def test_authenticated_user_can_delete_their_own_trip(client):
    headers, user_id = await create_user_and_headers(client, "TripDeleter")
    create_res = await client.post("/api/v1/trips/plan", json=sample_trip_payload(), headers=headers)
    trip_id = create_res.json()["trip_id"]

    del_res = await client.delete(f"/api/v1/trips/{trip_id}", headers=headers)
    assert del_res.status_code == 200
    assert del_res.json()["message"] == "Trip deleted successfully"

    # Subsequent GET returns 404
    get_res = await client.get(f"/api/v1/trips/{trip_id}", headers=headers)
    assert get_res.status_code == 404

    # DB verification
    with SessionLocal() as db:
        trip = db.query(Trip).filter(Trip.id == trip_id).first()
        assert trip is None


# 10. /api/v1/users/me/trips returns only owned trips
@pytest.mark.asyncio
async def test_users_me_trips_returns_only_owned_trips(client):
    headers_1, user_1 = await create_user_and_headers(client, "IsolatedUser1")
    headers_2, user_2 = await create_user_and_headers(client, "IsolatedUser2")

    # User 1 creates 2 trips
    t1 = await client.post("/api/v1/trips/plan", json=sample_trip_payload(destination="User1-Trip1"), headers=headers_1)
    t2 = await client.post("/api/v1/trips/plan", json=sample_trip_payload(destination="User1-Trip2"), headers=headers_1)
    assert t1.status_code == 200
    assert t2.status_code == 200

    # User 2 creates 1 trip
    t3 = await client.post("/api/v1/trips/plan", json=sample_trip_payload(destination="User2-Trip1"), headers=headers_2)
    assert t3.status_code == 200

    # User 1 queries /api/v1/users/me/trips
    me_res_1 = await client.get("/api/v1/users/me/trips", headers=headers_1)
    assert me_res_1.status_code == 200
    trips_1 = me_res_1.json()
    assert len(trips_1) == 2
    assert all(t["user_id"] == user_1 for t in trips_1)
    destinations_1 = {t["destination"] for t in trips_1}
    assert destinations_1 == {"User1-Trip1", "User1-Trip2"}

    # User 2 queries /api/v1/users/me/trips
    me_res_2 = await client.get("/api/v1/users/me/trips", headers=headers_2)
    assert me_res_2.status_code == 200
    trips_2 = me_res_2.json()
    assert len(trips_2) == 1
    assert trips_2[0]["user_id"] == user_2
    assert trips_2[0]["destination"] == "User2-Trip1"
