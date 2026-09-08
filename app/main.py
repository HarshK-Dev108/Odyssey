from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.api.routes import health, trips, users
from app.api.routes.tourism import tourism_router
from app.core.database import Base, engine
from app.core.mongodb import connect_to_mongo, close_mongo_connection, get_database
from app.core.indexes import create_indexes
from app.models.trip import Trip
from app.models.user import User


# Create database tables when the application starts
Base.metadata.create_all(bind=engine)


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


app.include_router(health.router)
app.include_router(trips.router)
app.include_router(users.router)
app.include_router(tourism_router)
