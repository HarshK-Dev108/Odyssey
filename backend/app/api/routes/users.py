from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token
)
from app.models.user import User


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