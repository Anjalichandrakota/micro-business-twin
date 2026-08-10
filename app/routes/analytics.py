"""
Analytics & Dashboard API routes.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.business import Business
from app.routes.deps import get_current_user
from app.services.analytics import compute_analytics, compute_whatif

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("", summary="Get full analytics for the current business")
def get_analytics(
    date_from: str = Query(None, description="Start date YYYY-MM-DD"),
    date_to: str = Query(None, description="End date YYYY-MM-DD"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Compute and return comprehensive business analytics."""
    business = db.query(Business).filter(Business.owner_id == current_user.id).first()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found.")

    analytics = compute_analytics(db, business.id, date_from=date_from, date_to=date_to)
    analytics["business"] = {
        "id": business.id,
        "business_name": business.business_name,
        "business_type": business.business_type,
        "location": business.location,
        "currency": business.currency,
    }
    return analytics


@router.get("/products", summary="Get product list for the current business")
def get_products(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return list of unique products for the business."""
    business = db.query(Business).filter(Business.owner_id == current_user.id).first()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found.")

    from app.models.data import Sales
    products = db.query(Sales.product).filter(
        Sales.business_id == business.id
    ).distinct().all()

    return {"products": [p[0] for p in products if p[0]]}


@router.post("/whatif", summary="Run a what-if scenario")
def run_whatif(
    scenario: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Run a what-if business scenario and return projected impact."""
    business = db.query(Business).filter(Business.owner_id == current_user.id).first()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found.")

    if not scenario.get("type"):
        raise HTTPException(status_code=400, detail="Scenario type is required.")

    result = compute_whatif(db, business.id, scenario)
    return result
