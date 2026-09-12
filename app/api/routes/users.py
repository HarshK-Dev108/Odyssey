from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.auth import get_current_user
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token
)
from app.models.user import User
from app.models.trip import Trip


router = APIRouter(
    prefix="/api/v1/users",
    tags=["Users"]
)


@router.post("/")
def create_user(
    name: str,
    email: str,
    password: str,
    db: Session = Depends(get_db)
):
    # Check if email already exists
    existing_user = db.query(User).filter(
        User.email == email
    ).first()

    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )

    # Hash password before saving
    password_hash = hash_password(password)

    new_user = User(
        name=name,
        email=email,
        password_hash=password_hash
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {
        "message": "User created successfully",
        "user_id": new_user.id,
        "name": new_user.name,
        "email": new_user.email
    }


# Login user
@router.post("/login")
def login_user(
    email: str,
    password: str,
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(
        User.email == email
    ).first()

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    if not verify_password(
        password,
        user.password_hash
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    # Create JWT access token
    access_token = create_access_token({
        "user_id": user.id
    })

    return {
        "message": "Login successful",
        "user_id": user.id,
        "name": user.name,
        "email": user.email,
        "access_token": access_token,
        "token_type": "bearer"
    }


def serialize_trip(trip: Trip) -> dict:
    return {
        "trip_id": trip.id,
        "id": trip.id,
        "user_id": trip.user_id,
        "from_city": trip.from_city,
        "destination": trip.destination,
        "start_date": trip.start_date,
        "end_date": trip.end_date,
        "travellers": trip.travellers,
        "budget": trip.budget,
        "currency": trip.currency,
        "interests": trip.interests,
        "hotel_rating": trip.hotel_rating,
        "pace": trip.pace,
        "avoid_crowds": trip.avoid_crowds,
        "ai_plan": trip.ai_plan
    }


@router.get("/me/trips")
def get_current_user_trips(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    trips = (
        db.query(Trip)
        .filter(Trip.user_id == current_user.id)
        .order_by(Trip.id.desc())
        .all()
    )
    return [serialize_trip(trip) for trip in trips]