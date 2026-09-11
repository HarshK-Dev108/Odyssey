from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class WeatherQuery(BaseModel):
    latitude: float = Field(..., ge=-90.0, le=90.0, description="Latitude coordinate")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="Longitude coordinate")


class WeatherResponse(BaseModel):
    latitude: float
    longitude: float
    temperature: float = Field(..., description="Current temperature in Celsius")
    condition: str = Field(..., description="Weather condition description")
    weather_code: Optional[int] = Field(None, description="WMO weather interpretation code")
    humidity: Optional[float] = Field(None, description="Relative humidity percentage")
    wind_speed: Optional[float] = Field(None, description="Wind speed in km/h")
    unit: str = Field(default="Celsius", description="Temperature unit")
    timestamp: datetime = Field(..., description="Observation timestamp")

    model_config = {
        "json_schema_extra": {
            "example": {
                "latitude": 26.9124,
                "longitude": 75.7873,
                "temperature": 28.5,
                "condition": "Clear sky",
                "weather_code": 0,
                "humidity": 42.0,
                "wind_speed": 12.4,
                "unit": "Celsius",
                "timestamp": "2026-03-15T12:00:00Z"
            }
        }
    }
