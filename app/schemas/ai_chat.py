from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field

from app.schemas.itinerary import ItineraryResponse


class SupportedIntent(str, Enum):
    MAKE_TRIP_CHEAPER = "make_trip_cheaper"
    CHANGE_HOTEL = "change_hotel"
    ADD_ACTIVITY = "add_activity"
    REMOVE_ACTIVITY = "remove_activity"
    REPLACE_ACTIVITY = "replace_activity"
    MORE_ADVENTURE = "more_adventure"
    MORE_RELAXED = "more_relaxed"
    WEATHER_SAFE_PLAN = "weather_safe_plan"
    EXPLAIN_ITINERARY = "explain_itinerary"
    UNKNOWN = "unknown"


class AIChatRequest(BaseModel):
    trip_id: int = Field(..., description="ID of the user's trip")
    message: str = Field(..., min_length=2, description="Natural language request or instruction")


class AIActionParameters(BaseModel):
    target_savings: Optional[float] = Field(None, description="Requested amount to save in trip currency")
    hotel_name: Optional[str] = Field(None, description="Preferred hotel name to swap to")
    hotel_rating: Optional[float] = Field(None, description="Desired minimum hotel star rating")
    activity_name: Optional[str] = Field(None, description="Name of activity to add or remove")
    current_activity_name: Optional[str] = Field(None, description="Existing activity to be replaced")
    new_activity_name: Optional[str] = Field(None, description="New activity to substitute in")
    category: Optional[str] = Field(None, description="Activity category (e.g. Adventure, Culture, Food)")
    day_number: Optional[int] = Field(None, description="Specific day for activity operation")
    time_slot: Optional[str] = Field(None, description="Slot: morning, afternoon, or evening")
    item_id: Optional[int] = Field(None, description="Specific SQLite ItineraryItem ID")


class AIStructuredAction(BaseModel):
    intent: SupportedIntent = Field(..., description="Normalized intent classified by YatraAI")
    parameters: AIActionParameters = Field(default_factory=AIActionParameters, description="Parameters extracted from message")
    reasoning: Optional[str] = Field(None, description="Short rationale for the chosen action")


class BudgetComparison(BaseModel):
    previous_total: float = Field(..., description="Total cost before applying action")
    updated_total: float = Field(..., description="Total cost after applying action")
    difference: float = Field(..., description="Net cost difference (updated - previous)")
    savings: float = Field(0.0, description="Positive savings achieved if difference is negative, else 0.0")
    currency: str = Field("INR", description="Currency code")


class AIChatResponse(BaseModel):
    trip_id: int
    intent: str
    status: str = Field(..., description="'applied', 'no_change', 'explained', 'unsupported', or 'error'")
    message: str
    changes_made: List[str] = Field(default_factory=list)
    budget_comparison: BudgetComparison
    itinerary: Optional[ItineraryResponse] = None
