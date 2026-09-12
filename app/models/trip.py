from sqlalchemy import Column, Integer, String, Float, Date, JSON, Boolean, ForeignKey
from sqlalchemy.orm import relationship

from app.core.database import Base


class Trip(Base):
    __tablename__ = "trips"

    id = Column(Integer, primary_key=True, index=True)

    # Nullable keeps legacy trips readable while ownership is migrated.
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)

    from_city = Column(String, nullable=False)
    destination = Column(String, nullable=False)

    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)

    travellers = Column(Integer, nullable=False)
    budget = Column(Float, nullable=False)

    currency = Column(String, default="INR")

    interests = Column(JSON, default=list)

    hotel_rating = Column(Integer, default=3)
    pace = Column(String, default="moderate")
    avoid_crowds = Column(Boolean, default=False)

    # Stores the latest AI-generated/optimized travel plan
    ai_plan = Column(JSON, nullable=True)

    owner = relationship("User", back_populates="trips")
    itinerary = relationship(
        "Itinerary",
        back_populates="trip",
        uselist=False,
        cascade="all, delete-orphan"
    )

    @property
    def user(self):
        return self.owner