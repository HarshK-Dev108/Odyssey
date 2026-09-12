from datetime import datetime
from typing import Optional, List, Literal
from pydantic import BaseModel, Field


class ItineraryItemBase(BaseModel):
    day_number: int = Field(..., ge=1, description="Day index of the trip (1-indexed)")
    time_slot: Optional[str] = Field(None, description="Time slot, e.g. morning, afternoon, evening")
    activity_id: Optional[str] = Field(None, description="MongoDB Activity ObjectId string")
    title_override: Optional[str] = Field(None, description="Custom title or description override")
    start_time: Optional[str] = Field(None, description="Scheduled start time, e.g. '09:00'")
    duration_minutes: Optional[int] = Field(None, gt=0, description="Duration in minutes")
    estimated_cost: float = Field(default=0.0, ge=0.0, description="Estimated cost for this item")


class ItineraryItemCreate(ItineraryItemBase):
    pass


class ItineraryItemResponse(ItineraryItemBase):
    id: int
    itinerary_id: int

    model_config = {"from_attributes": True}


class ItineraryResponse(BaseModel):
    id: int
    trip_id: int
    selected_hotel_id: Optional[str] = None
    outbound_flight_id: Optional[str] = None
    return_flight_id: Optional[str] = None
    estimated_total_cost: float = 0.0
    created_at: datetime
    updated_at: datetime
    items: List[ItineraryItemResponse] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class HotelSelectionRequest(BaseModel):
    hotel_id: Optional[str] = Field(None, description="MongoDB Hotel ObjectId string, or null to remove hotel")


class FlightsSelectionRequest(BaseModel):
    outbound_flight_id: Optional[str] = Field(None, description="MongoDB Flight ObjectId for outbound flight")
    return_flight_id: Optional[str] = Field(None, description="MongoDB Flight ObjectId for return flight")


class ActivityMutationRequest(BaseModel):
    action: Literal["add", "remove", "replace"] = Field(
        default="add",
        description="Mutation action to perform: 'add', 'remove', or 'replace'"
    )
    item_id: Optional[int] = Field(None, description="ID of ItineraryItem to remove or replace")
    day_number: Optional[int] = Field(None, ge=1, description="Day index (for add / replace)")
    time_slot: Optional[str] = Field(None, description="Time slot, e.g. morning, afternoon, evening")
    activity_id: Optional[str] = Field(None, description="MongoDB Activity ObjectId string")
    title_override: Optional[str] = Field(None, description="Custom title or description override")
    start_time: Optional[str] = Field(None, description="Scheduled start time, e.g. '09:00'")
    duration_minutes: Optional[int] = Field(None, gt=0, description="Duration in minutes")
    estimated_cost: Optional[float] = Field(None, ge=0.0, description="Estimated cost")
    items: Optional[List[ItineraryItemCreate]] = Field(None, description="Complete replacement list for bulk replace")
