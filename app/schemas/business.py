"""
Pydantic schemas for the Business domain.
"""

from datetime import datetime
from pydantic import BaseModel, Field


class BusinessBase(BaseModel):
    business_name: str = Field(..., min_length=2, max_length=255)
    business_type: str = Field(..., min_length=2, max_length=100)
    location: str = Field(..., min_length=2, max_length=255)
    currency: str = Field(..., min_length=2, max_length=10)


class BusinessCreate(BusinessBase):
    pass


class BusinessUpdate(BusinessBase):
    pass


class BusinessResponse(BusinessBase):
    id: int
    owner_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
