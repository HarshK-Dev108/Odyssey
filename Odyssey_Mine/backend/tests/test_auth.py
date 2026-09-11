from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from jose import jwt

from app.core.database import SessionLocal
from app.core.security import ALGORITHM, SECRET_KEY, create_access_token
from app.models.trip import Trip


async def register_and_login(client, name):
    email = f"{name.lower()}-{uuid4().hex}@odyssey.com"
    registration = await client.post(
        "/api/v1/users/",
        params={"name": name, "email": email, "password": "password123"},
    )
    assert registration.status_code == 200

    login = await client.post(
        "/api/v1/users/login",
        params={"email": email, "password": "password123"},
    )
    assert login.status_code == 200
    body = login.json()
    return {
        "Authorization": f"Bearer {body['access_token']}"
    }, body["user_id"], body


async def create_owned_trip(client, headers):
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
        headers=headers,
    )
    assert response.status_code == 200
    return response.json()["trip_id"]


@pytest.mark.asyncio
async def test_missing_invalid_expired_and_unknown_tokens_return_401(client):
    missing = await client.get("/api/v1/trips/1")
    assert missing.status_code == 401

    invalid = await client.get(
        "/api/v1/trips/1",
        headers={"Authorization": "Bearer invalid-token"},
    )
    assert invalid.status_code == 401

    expired_token = jwt.encode(
        {
            "user_id": 1,
            "exp": datetime.now(timezone.utc) - timedelta(minutes=1),
        },
        SECRET_KEY,
        algorithm=ALGORITHM,
    )
    expired = await client.get(
        "/api/v1/trips/1",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert expired.status_code == 401

    unknown_token = create_access_token({"user_id": 999999999})
    unknown = await client.get(
        "/api/v1/trips/1",
        headers={"Authorization": f"Bearer {unknown_token}"},
    )
    assert unknown.status_code == 401


@pytest.mark.asyncio
async def test_trip_is_owned_by_authenticated_user(client):
    headers, user_id, _ = await register_and_login(client, "Owner")
    trip_id = await create_owned_trip(client, headers)

    with SessionLocal() as db:
        trip = db.query(Trip).filter(Trip.id == trip_id).first()
        assert trip is not None
        assert trip.user_id == user_id

    response = await client.get(f"/api/v1/trips/{trip_id}", headers=headers)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_user_cannot_access_or_modify_another_users_trip(client):
    owner_headers, _, _ = await register_and_login(client, "TripOwner")
    other_headers, _, _ = await register_and_login(client, "OtherUser")
    trip_id = await create_owned_trip(client, owner_headers)

    get_response = await client.get(
        f"/api/v1/trips/{trip_id}", headers=other_headers
    )
    assert get_response.status_code == 404

    optimize_response = await client.post(
        f"/api/v1/trips/{trip_id}/optimize",
        json={"request": "make it cheaper"},
        headers=other_headers,
    )
    assert optimize_response.status_code == 404

    chat_response = await client.post(
        f"/api/v1/trips/{trip_id}/chat",
        json={"message": "how much budget is left?"},
        headers=other_headers,
    )
    assert chat_response.status_code == 404


@pytest.mark.asyncio
async def test_password_hash_is_never_returned_and_catalog_is_public(client):
    headers, _, login_body = await register_and_login(client, "ResponseUser")
    assert "password_hash" not in login_body

    public_catalog = await client.get("/api/v1/destinations")
    assert public_catalog.status_code == 200

    protected_catalog_data = await client.get(
        "/api/v1/expenses?trip_id=1",
        headers=headers,
    )
    assert protected_catalog_data.status_code == 404
