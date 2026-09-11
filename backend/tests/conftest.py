import pytest
import pytest_asyncio
import httpx
from mongomock_motor import AsyncMongoMockClient
from uuid import uuid4
from app.main import app
from app.core.mongodb import get_database, db_manager


@pytest_asyncio.fixture
async def mock_mongo_db():
    """Provides a fresh isolated in-memory Mock MongoDB database for each test."""
    mock_client = AsyncMongoMockClient()
    db = mock_client["test_tourism_db"]
    return db


@pytest_asyncio.fixture
async def client(mock_mongo_db):
    """Provides an AsyncClient connected to the FastAPI app with mocked MongoDB."""
    # Override get_database dependency with in-memory mock DB
    app.dependency_overrides[get_database] = lambda: mock_mongo_db
    orig_client = db_manager.client
    orig_db = db_manager.db
    db_manager.client = mock_mongo_db.client
    db_manager.db = mock_mongo_db

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac

    # Clean up overrides
    app.dependency_overrides.clear()
    db_manager.client = orig_client
    db_manager.db = orig_db


@pytest_asyncio.fixture
async def auth_headers(client):
    email = f"test-{uuid4().hex}@odyssey.com"
    registration = await client.post(
        "/api/v1/users/",
        params={
            "name": "Authenticated Test User",
            "email": email,
            "password": "password123",
        },
    )
    assert registration.status_code == 200

    login = await client.post(
        "/api/v1/users/login",
        params={"email": email, "password": "password123"},
    )
    assert login.status_code == 200

    return {
        "Authorization": f"Bearer {login.json()['access_token']}"
    }
