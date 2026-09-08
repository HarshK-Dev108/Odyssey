from fastapi import APIRouter, Query, status
from app.schemas.weather import WeatherResponse
from app.services.weather_service import get_weather_forecast

router = APIRouter(
    prefix="/weather",
    tags=["Weather"]
)


@router.get(
    "",
    response_model=WeatherResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current weather for coordinates",
    description="Fetches live normalized weather observations for the specified latitude and longitude."
)
async def get_weather(
    latitude: float = Query(..., ge=-90.0, le=90.0, description="Latitude between -90 and 90"),
    longitude: float = Query(..., ge=-180.0, le=180.0, description="Longitude between -180 and 180")
) -> WeatherResponse:
    return await get_weather_forecast(latitude=latitude, longitude=longitude)
