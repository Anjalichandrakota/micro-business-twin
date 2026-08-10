"""
Models for data datasets, validation tracking, and final tables.
"""

from datetime import datetime, timezone

from sqlalchemy import String, DateTime, Integer, ForeignKey, Float, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class DatasetJob(Base):
    """Tracks uploaded files and their validation status."""
    __tablename__ = "dataset_jobs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id"), nullable=False, index=True)
    
    # original file info
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    data_type: Mapped[str] = mapped_column(String(50), nullable=False) # 'sales', 'inventory', 'expenses'
    
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="uploaded") # uploaded, validated, cleaned, saved
    
    # Store schema mapping and issues as JSON
    mapping: Mapped[dict] = mapped_column(JSON, nullable=True)
    issues: Mapped[dict] = mapped_column(JSON, nullable=True)
    stats: Mapped[dict] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    business = relationship("Business")


class Sales(Base):
    """Cleaned sales data."""
    __tablename__ = "sales"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id"), nullable=False, index=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("dataset_jobs.id"), nullable=True)
    
    date: Mapped[str] = mapped_column(String(50), nullable=True)
    product: Mapped[str] = mapped_column(String(255), nullable=True)
    quantity: Mapped[float] = mapped_column(Float, nullable=True)
    price: Mapped[float] = mapped_column(Float, nullable=True)
    total_sales: Mapped[float] = mapped_column(Float, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )


class Inventory(Base):
    """Cleaned inventory data."""
    __tablename__ = "inventory"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id"), nullable=False, index=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("dataset_jobs.id"), nullable=True)
    
    product: Mapped[str] = mapped_column(String(255), nullable=True)
    sku: Mapped[str] = mapped_column(String(100), nullable=True)
    quantity: Mapped[float] = mapped_column(Float, nullable=True)
    location: Mapped[str] = mapped_column(String(255), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )


class Expenses(Base):
    """Cleaned expenses data."""
    __tablename__ = "expenses"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id"), nullable=False, index=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("dataset_jobs.id"), nullable=True)
    
    date: Mapped[str] = mapped_column(String(50), nullable=True)
    category: Mapped[str] = mapped_column(String(255), nullable=True)
    amount: Mapped[float] = mapped_column(Float, nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
