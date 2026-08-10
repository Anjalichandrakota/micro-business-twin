"""
Business routes: create, get, update.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.business import Business
from app.schemas.business import BusinessCreate, BusinessUpdate, BusinessResponse
from app.routes.deps import get_current_user

router = APIRouter(prefix="/api/business", tags=["business"])


@router.post(
    "",
    response_model=BusinessResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new business profile",
)
def create_business(
    body: BusinessCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new business for the authenticated user."""
    # Check if user already has a business
    existing = db.query(Business).filter(Business.owner_id == current_user.id).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You already have a business profile.",
        )

    business = Business(
        owner_id=current_user.id,
        business_name=body.business_name,
        business_type=body.business_type,
        location=body.location,
        currency=body.currency,
    )
    db.add(business)
    db.commit()
    db.refresh(business)
    return business


@router.get(
    "",
    response_model=BusinessResponse,
    summary="Get the current user's business",
)
def get_business(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get the business profile for the authenticated user."""
    business = db.query(Business).filter(Business.owner_id == current_user.id).first()
    if not business:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Business profile not found.",
        )
    return business


@router.put(
    "/{business_id}",
    response_model=BusinessResponse,
    summary="Update the business profile",
)
def update_business(
    business_id: int,
    body: BusinessUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update an existing business profile."""
    business = db.query(Business).filter(Business.id == business_id).first()
    
    if not business:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Business profile not found.",
        )
        
    if business.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to modify this business.",
        )

    business.business_name = body.business_name
    business.business_type = body.business_type
    business.location = body.location
    business.currency = body.currency

    db.commit()
    db.refresh(business)
    return business
