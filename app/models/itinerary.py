from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.orm import relationship

from app.core.database import Base


class Itinerary(Base):
    __tablename__ = "itineraries"

    id = Column(Integer, primary_key=True, index=True)
    trip_id = Column(
        Integer,
        ForeignKey("trips.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True
    )

    # MongoDB ObjectIds stored as scalar strings (no cross-database foreign keys)
    selected_hotel_id = Column(String, nullable=True)
    outbound_flight_id = Column(String, nullable=True)
    return_flight_id = Column(String, nullable=True)

    estimated_total_cost = Column(Float, default=0.0, nullable=False)

    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    trip = relationship("Trip", back_populates="itinerary")
    items = relationship(
        "ItineraryItem",
        back_populates="itinerary",
        cascade="all, delete-orphan",
        order_by="ItineraryItem.day_number, ItineraryItem.id"
    )


class ItineraryItem(Base):
    __tablename__ = "itinerary_items"

    id = Column(Integer, primary_key=True, index=True)
    itinerary_id = Column(
        Integer,
        ForeignKey("itineraries.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    day_number = Column(Integer, nullable=False)
    time_slot = Column(String, nullable=True)  # e.g. "morning", "afternoon", "evening"
    activity_id = Column(String, nullable=True)  # MongoDB Activity ObjectId string

    title_override = Column(String, nullable=True)
    start_time = Column(String, nullable=True)  # e.g. "09:00"
    duration_minutes = Column(Integer, nullable=True)
    estimated_cost = Column(Float, default=0.0, nullable=False)

    itinerary = relationship("Itinerary", back_populates="items")
