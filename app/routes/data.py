"""
Data upload, validation, and confirmation routes for the business owner.
"""
import os
import shutil
import json
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
import pandas as pd
import numpy as np

from app.database import get_db
from app.models.user import User
from app.models.business import Business
from app.models.data import DatasetJob, Sales, Inventory, Expenses
from app.routes.deps import get_current_user
from app.core import UPLOAD_DIR
from app.services.validation import detect_schema, validate_data, clean_data

router = APIRouter(prefix="/api/data", tags=["data"])


@router.post("/upload", summary="Upload business data file (CSV/Excel)")
def upload_data(
    data_type: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    business = db.query(Business).filter(Business.owner_id == current_user.id).first()
    if not business:
        raise HTTPException(status_code=400, detail="You must set up your business first.")

    allowed_types = ["sales", "products", "inventory", "expenses"]
    if data_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Invalid data type.")

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in [".csv", ".xlsx", ".xls"]:
        raise HTTPException(status_code=400, detail="Only CSV and Excel allowed.")

    business_dir = os.path.join(UPLOAD_DIR, str(business.id))
    os.makedirs(business_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_filename = f"{data_type}_{timestamp}_{file.filename}"
    file_path = os.path.join(business_dir, safe_filename)

    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception:
        raise HTTPException(status_code=500, detail="Error saving file to disk.")

    job = DatasetJob(
        business_id=business.id,
        filename=file.filename,
        file_path=file_path,
        data_type=data_type,
        status="uploaded"
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    return {"job_id": job.id, "message": "File uploaded successfully."}


@router.get("/validate/{job_id}", summary="Get validation report for a job")
def get_validation(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    business = db.query(Business).filter(Business.owner_id == current_user.id).first()
    if not business:
        raise HTTPException(status_code=400, detail="Business not found.")
        
    job = db.query(DatasetJob).filter(DatasetJob.id == job_id, DatasetJob.business_id == business.id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Dataset job not found.")

    if not os.path.exists(job.file_path):
        raise HTTPException(status_code=404, detail="File no longer exists.")

    try:
        if job.file_path.endswith(".csv"):
            df = pd.read_csv(job.file_path)
        else:
            df = pd.read_excel(job.file_path)
    except Exception:
        raise HTTPException(status_code=400, detail="Failed to read the file.")

    # Re-run mapping and validation every time unless it's already saved
    mapping = detect_schema(df, job.data_type)
    report = validate_data(df, job.data_type, mapping)
    
    job.mapping = mapping
    job.stats = {
        "total_rows": report["total_rows"],
        "valid_rows": report["valid_rows"],
        "duplicates": report["duplicates"]
    }
    job.issues = report["issues"]
    
    if job.status == "uploaded":
        job.status = "validated"
    
    db.commit()

    return {
        "job_id": job.id,
        "filename": job.filename,
        "data_type": job.data_type,
        "status": job.status,
        "stats": job.stats,
        "mapping": job.mapping,
        "issues": job.issues
    }


@router.post("/clean/{job_id}", summary="Clean the dataset and re-validate")
def perform_clean(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    business = db.query(Business).filter(Business.owner_id == current_user.id).first()
    if not business:
        raise HTTPException(status_code=400, detail="Business not found.")
        
    job = db.query(DatasetJob).filter(DatasetJob.id == job_id, DatasetJob.business_id == business.id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Dataset job not found.")

    if job.status == "saved":
        raise HTTPException(status_code=400, detail="Dataset is already saved.")

    try:
        if job.file_path.endswith(".csv"):
            df = pd.read_csv(job.file_path)
        else:
            df = pd.read_excel(job.file_path)
    except Exception:
        raise HTTPException(status_code=400, detail="Failed to read the file.")

    mapping = job.mapping or detect_schema(df, job.data_type)
    clean_df = clean_data(df, job.data_type, mapping)
    
    # Save cleaned data to a new file, replacing the old one
    if job.file_path.endswith(".csv"):
        clean_df.to_csv(job.file_path, index=False)
    else:
        clean_df.to_excel(job.file_path, index=False)

    report = validate_data(clean_df, job.data_type, mapping)
    
    job.stats = {
        "total_rows": report["total_rows"],
        "valid_rows": report["valid_rows"],
        "duplicates": report["duplicates"]
    }
    job.issues = report["issues"]
    job.status = "cleaned"
    db.commit()

    return {
        "job_id": job.id,
        "status": job.status,
        "stats": job.stats,
        "issues": job.issues,
        "message": "Data cleaned successfully."
    }


@router.post("/confirm/{job_id}", summary="Confirm and save clean data to the database")
def confirm_data(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    business = db.query(Business).filter(Business.owner_id == current_user.id).first()
    if not business:
        raise HTTPException(status_code=400, detail="Business not found.")
        
    job = db.query(DatasetJob).filter(DatasetJob.id == job_id, DatasetJob.business_id == business.id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Dataset job not found.")

    if job.status == "saved":
        raise HTTPException(status_code=400, detail="Dataset is already saved.")

    try:
        if job.file_path.endswith(".csv"):
            df = pd.read_csv(job.file_path)
        else:
            df = pd.read_excel(job.file_path)
    except Exception:
        raise HTTPException(status_code=400, detail="Failed to read the file.")

    # Replace nan with None for DB insertion
    df = df.replace({np.nan: None})
    
    mapping = job.mapping
    inv_map = {v: k for k, v in mapping.items()}

    records = []
    for _, row in df.iterrows():
        if job.data_type == "sales":
            r = Sales(
                business_id=business.id,
                job_id=job.id,
                date=row.get(inv_map.get("date")),
                product=row.get(inv_map.get("product")),
                quantity=row.get(inv_map.get("quantity")),
                price=row.get(inv_map.get("price")),
                total_sales=row.get(inv_map.get("total_sales")),
            )
        elif job.data_type == "inventory":
            r = Inventory(
                business_id=business.id,
                job_id=job.id,
                product=row.get(inv_map.get("product")),
                sku=row.get(inv_map.get("sku")),
                quantity=row.get(inv_map.get("quantity")),
                location=row.get(inv_map.get("location")),
            )
        elif job.data_type == "expenses":
            r = Expenses(
                business_id=business.id,
                job_id=job.id,
                date=row.get(inv_map.get("date")),
                category=row.get(inv_map.get("category")),
                amount=row.get(inv_map.get("amount")),
                description=row.get(inv_map.get("description")),
            )
        else:
            continue
        records.append(r)

    db.add_all(records)
    job.status = "saved"
    db.commit()

    return {"message": "Data saved successfully.", "records_inserted": len(records)}
