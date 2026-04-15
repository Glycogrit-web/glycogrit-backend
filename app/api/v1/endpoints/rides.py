from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from app.core.database import get_db
from app.middleware.auth import get_current_user
from app.models.user import User
from app.models.ride import Ride, RideStatus
from app.schemas.ride import RideCreate, RideUpdate, RideResponse

router = APIRouter()


@router.get("/", response_model=List[RideResponse])
def get_rides(
    skip: int = 0,
    limit: int = 100,
    status: Optional[RideStatus] = None,
    city: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get all rides with optional filters.
    """
    query = db.query(Ride)

    if status:
        query = query.filter(Ride.status == status)

    if city:
        query = query.filter(Ride.start_location.ilike(f"%{city}%"))

    rides = query.offset(skip).limit(limit).all()
    return rides


@router.get("/{ride_id}", response_model=RideResponse)
def get_ride(
    ride_id: int,
    db: Session = Depends(get_db)
):
    """
    Get ride by ID.
    """
    ride = db.query(Ride).filter(Ride.id == ride_id).first()
    if not ride:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ride not found"
        )
    return ride


@router.post("/", response_model=RideResponse, status_code=status.HTTP_201_CREATED)
def create_ride(
    ride: RideCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new ride.
    """
    db_ride = Ride(
        **ride.model_dump(),
        organizer_id=current_user.id
    )
    db.add(db_ride)
    db.commit()
    db.refresh(db_ride)
    return db_ride


@router.put("/{ride_id}", response_model=RideResponse)
def update_ride(
    ride_id: int,
    ride_update: RideUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update a ride (only organizer can update).
    """
    db_ride = db.query(Ride).filter(Ride.id == ride_id).first()
    if not db_ride:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ride not found"
        )

    # Check if user is the organizer
    if db_ride.organizer_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the organizer can update this ride"
        )

    # Update ride fields
    update_data = ride_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_ride, field, value)

    db.commit()
    db.refresh(db_ride)
    return db_ride


@router.delete("/{ride_id}")
def delete_ride(
    ride_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete a ride (only organizer can delete).
    """
    db_ride = db.query(Ride).filter(Ride.id == ride_id).first()
    if not db_ride:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ride not found"
        )

    # Check if user is the organizer
    if db_ride.organizer_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the organizer can delete this ride"
        )

    db.delete(db_ride)
    db.commit()
    return {"message": "Ride deleted successfully"}


@router.get("/upcoming/all", response_model=List[RideResponse])
def get_upcoming_rides(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """
    Get all upcoming rides.
    """
    rides = db.query(Ride).filter(
        Ride.status == RideStatus.UPCOMING,
        Ride.start_time > datetime.now()
    ).offset(skip).limit(limit).all()
    return rides
