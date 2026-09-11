from fastapi import APIRouter

from app.api.routes import destinations, hotels, flights, activities, expenses, weather

tourism_router = APIRouter(prefix="/api/v1")

tourism_router.include_router(destinations.router)
tourism_router.include_router(hotels.router)
tourism_router.include_router(flights.router)
tourism_router.include_router(activities.router)
tourism_router.include_router(expenses.router)
tourism_router.include_router(weather.router)
