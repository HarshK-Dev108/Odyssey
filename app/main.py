from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os

from app.api.routes import health, trips, users, optimization, assistant, itineraries
from app.api.routes.tourism import tourism_router
from app.core.database import Base, engine, ensure_legacy_schema
from app.core.mongodb import connect_to_mongo, close_mongo_connection, get_database
from app.core.indexes import create_indexes
from app.models.trip import Trip
from app.models.user import User
from app.models.itinerary import Itinerary, ItineraryItem


# Create database tables when the application starts
Base.metadata.create_all(bind=engine)
ensure_legacy_schema()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize MongoDB and ensure indexes
    await connect_to_mongo()
    db = get_database()
    await create_indexes(db)
    yield
    # Shutdown: Cleanly close MongoDB client
    await close_mongo_connection()


app = FastAPI(
    title="AI Smart Travel Planner",
    version="1.0.0",
    lifespan=lifespan
)

allowed_origins = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173").split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(health.router)
app.include_router(trips.router)
app.include_router(users.router)
app.include_router(tourism_router)
app.include_router(optimization.router)
app.include_router(assistant.router)
app.include_router(itineraries.router)