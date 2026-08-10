"""
AI Assistant API routes — conversational business assistant.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.models.user import User
from app.models.business import Business
from app.routes.deps import get_current_user
from app.services.analytics import compute_analytics
from app.services.ai_assistant import ask_assistant

router = APIRouter(prefix="/api/assistant", tags=["assistant"])


class ChatMessage(BaseModel):
    role: str = Field(..., description="user or assistant")
    content: str


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    history: Optional[list[ChatMessage]] = None


@router.post("", summary="Ask the AI Business Assistant a question")
async def chat_with_assistant(
    body: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Send a question to the AI assistant, grounded in business data."""
    business = db.query(Business).filter(Business.owner_id == current_user.id).first()
    if not business:
        raise HTTPException(status_code=404, detail="Set up your business first.")

    # Get current analytics
    analytics = compute_analytics(db, business.id)

    business_info = {
        "business_name": business.business_name,
        "business_type": business.business_type,
        "location": business.location,
        "currency": business.currency,
    }

    # Convert history
    history = None
    if body.history:
        history = [{"role": m.role, "content": m.content} for m in body.history]

    # Ask AI
    response = await ask_assistant(
        question=body.question,
        business_info=business_info,
        analytics=analytics,
        conversation_history=history,
    )

    return {
        "response": response,
        "has_data": analytics.get("has_sales", False) or analytics.get("has_inventory", False) or analytics.get("has_expenses", False),
    }
