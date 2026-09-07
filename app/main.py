from fastapi import FastAPI

from app.api.routes import health, trips, users
from app.core.database import Base, engine
from app.models.trip import Trip
from app.models.user import User


# Create database tables when the application starts
Base.metadata.create_all(bind=engine)


app = FastAPI(
    title="AI Smart Travel Planner",
    version="1.0.0"
)


app.include_router(health.router)
app.include_router(trips.router)
app.include_router(users.router)