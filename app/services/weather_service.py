import os
import logging
from datetime import datetime, timezone
import httpx
from fastapi import HTTPException
from app.schemas.weather import WeatherResponse

logger = logging.getLogger(__name__)

WEATHER_API_URL = os.getenv("WEATHER_API_URL", "https://api.open-meteo.com/v1/forecast")

# WMO Weather interpretation codes (WW)
WMO_CODE_MAP = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    71: "Slight snow fall",
    73: "Moderate snow fall",
    75: "Heavy snow fall",
    77: "Snow grains",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}


def interpret_weather_code(code: int | None) -> str:
    if code is None:
        return "Unknown"
    return WMO_CODE_MAP.get(code, "Variable weather")


async def get_weather_forecast(latitude: float, longitude: float) -> WeatherResponse:
    """
    Fetch current weather forecast for given coordinates using Open-Meteo API.
    Raises HTTPException(503) if external provider is unreachable, times out, or fails.
    """
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": "temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m"
    }

    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            response = await client.get(WEATHER_API_URL, params=params)

            if response.status_code != 200:
                logger.error(f"Weather provider returned status {response.status_code}: {response.text}")
                raise HTTPException(
                    status_code=503,
                    detail=f"Weather service provider error (Status {response.status_code})"
                )

            data = response.json()
            current = data.get("current", {})

            temp = current.get("temperature_2m")
            if temp is None:
                raise HTTPException(
                    status_code=502,
                    detail="Invalid payload received from weather provider"
                )

            weather_code = current.get("weather_code")
            humidity = current.get("relative_humidity_2m")
            wind_speed = current.get("wind_speed_10m")
            condition = interpret_weather_code(weather_code)

            return WeatherResponse(
                latitude=latitude,
                longitude=longitude,
                temperature=float(temp),
                condition=condition,
                weather_code=weather_code,
                humidity=float(humidity) if humidity is not None else None,
                wind_speed=float(wind_speed) if wind_speed is not None else None,
                unit="Celsius",
                timestamp=datetime.now(timezone.utc)
            )

    except httpx.TimeoutException as exc:
        logger.error(f"Timeout while connecting to weather service: {exc}")
        raise HTTPException(
            status_code=504,
            detail="Weather service request timed out"
        ) from exc
    except httpx.RequestError as exc:
        logger.error(f"Network error connecting to weather service: {exc}")
        raise HTTPException(
            status_code=503,
            detail="Failed to connect to weather service provider"
        ) from exc
