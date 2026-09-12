from typing import Optional, List, Dict
from pydantic import BaseModel, Field
from app.schemas.itinerary import ItineraryResponse


class BudgetBreakdown(BaseModel):
    hotel_cost: float = Field(default=0.0, description="Estimated total accommodation cost")
    flights_cost: float = Field(default=0.0, description="Estimated total flight tickets cost")
    activities_cost: float = Field(default=0.0, description="Estimated total scheduled activities cost")


class BudgetSummary(BaseModel):
    total_budget: float = Field(..., description="User's specified trip budget")
    estimated_total_cost: float = Field(..., description="Sum of hotel, flights, and activities")
    remaining_budget: float = Field(default=0.0, description="Remaining unallocated budget")
    over_budget_amount: float = Field(default=0.0, description="Amount exceeding budget if over budget")
    is_over_budget: bool = Field(default=False, description="True if estimated cost exceeds budget")
    breakdown: BudgetBreakdown = Field(default_factory=BudgetBreakdown)


class WeatherSummary(BaseModel):
    available: bool = Field(default=False, description="Whether live weather forecast was fetched")
    condition: Optional[str] = Field(None, description="Observed weather condition")
    temperature: Optional[float] = Field(None, description="Current temperature in Celsius")
    is_rainy: bool = Field(default=False, description="True if rain or adverse weather detected")
    rain_safe_prioritized: bool = Field(default=False, description="True if rain-safe activities were prioritized")


class ItineraryGenerationResponse(BaseModel):
    message: str = Field(..., description="Status summary message")
    trip_id: int = Field(..., description="ID of the trip")
    itinerary: ItineraryResponse = Field(..., description="The persisted itinerary object")
    budget_summary: BudgetSummary = Field(..., description="Budget breakdown and allocation analysis")
    weather_summary: WeatherSummary = Field(..., description="Weather forecast summary and impact")
    warnings: List[str] = Field(default_factory=list, description="Any warnings regarding budget, catalogue or weather")
