"""
Data validation and cleaning logic.
"""

import pandas as pd
import numpy as np

SCHEMAS = {
    "sales": {
        "date": ["sale date", "date", "transaction date"],
        "product": ["product name", "product", "item"],
        "quantity": ["qty", "quantity", "count"],
        "price": ["price", "unit price"],
        "total_sales": ["revenue", "total sales", "amount", "total"],
    },
    "inventory": {
        "product": ["product name", "product", "item"],
        "sku": ["sku", "item code", "code"],
        "quantity": ["qty", "quantity", "stock", "count"],
        "location": ["location", "warehouse", "store"],
    },
    "expenses": {
        "date": ["date", "expense date"],
        "category": ["category", "type", "expense type"],
        "amount": ["amount", "cost", "total"],
        "description": ["description", "notes", "details"],
    }
}

def detect_schema(df: pd.DataFrame, data_type: str) -> dict:
    """Attempts to automatically map DataFrame columns to expected schema."""
    if data_type not in SCHEMAS:
        return {}
        
    expected = SCHEMAS[data_type]
    mapping = {}
    cols = [str(c).lower().strip() for c in df.columns]
    
    for canon_col, aliases in expected.items():
        found = False
        # Exact alias match
        for i, col in enumerate(cols):
            if col in aliases:
                mapping[df.columns[i]] = canon_col
                found = True
                break
        
        # Substring alias match
        if not found:
            for i, col in enumerate(cols):
                if any(alias in col for alias in aliases) and df.columns[i] not in mapping:
                    mapping[df.columns[i]] = canon_col
                    break
                    
    return mapping


def validate_data(df: pd.DataFrame, data_type: str, mapping: dict) -> dict:
    """Validates the dataframe according to the mapped columns and business logic."""
    issues = []
    
    total_rows = len(df)
    valid_rows = total_rows
    
    # Check for missing required columns
    expected_cols = list(SCHEMAS.get(data_type, {}).keys())
    mapped_canon = list(mapping.values())
    
    for req in expected_cols:
        if req not in mapped_canon:
            issues.append({
                "type": "error",
                "row": "-",
                "message": f"Missing required column: {req}"
            })

    if issues:
        # If columns are missing, we can't reliably validate rows
        return {
            "total_rows": total_rows,
            "valid_rows": 0,
            "issues": issues,
            "duplicates": 0
        }

    # Reverse mapping for quick lookup
    inv_map = {v: k for k, v in mapping.items()}

    # Check duplicates
    duplicates = df.duplicated().sum()
    if duplicates > 0:
        issues.append({
            "type": "warning",
            "row": "-",
            "message": f"Found {duplicates} duplicate rows."
        })

    # Row by row validation (limit to 100 issues to avoid massive JSONs)
    issue_count = 0
    MAX_ISSUES = 100
    
    error_rows = set()

    for idx, row in df.iterrows():
        if issue_count >= MAX_ISSUES:
            break
            
        row_num = idx + 2 # 1-indexed plus header

        # --- Sales Validation ---
        if data_type == "sales":
            qty_col = inv_map.get("quantity")
            price_col = inv_map.get("price")
            total_col = inv_map.get("total_sales")
            prod_col = inv_map.get("product")
            
            qty = row.get(qty_col, 0)
            price = row.get(price_col, 0)
            total = row.get(total_col, 0)
            
            if pd.isna(qty) or pd.isna(price) or pd.isna(total):
                issues.append({"type": "error", "row": row_num, "message": "Missing numeric value (quantity, price, or total)."})
                error_rows.add(idx)
                issue_count += 1
                continue
                
            try:
                qty = float(qty)
                if qty < 0:
                    issues.append({"type": "error", "row": row_num, "message": "Invalid negative quantity."})
                    error_rows.add(idx)
                    issue_count += 1
            except ValueError:
                issues.append({"type": "error", "row": row_num, "message": "Quantity is not a number."})
                error_rows.add(idx)
                issue_count += 1
                
            try:
                price = float(price)
                total = float(total)
                # Warning if Qty * Price != Total
                if qty > 0 and price > 0 and abs((qty * price) - total) > 0.05:
                    issues.append({"type": "warning", "row": row_num, "message": "Sales total mismatch (Qty x Price != Total)."})
                    issue_count += 1
            except ValueError:
                pass
                
            if pd.isna(row.get(prod_col)) or str(row.get(prod_col)).strip() == "":
                issues.append({"type": "warning", "row": row_num, "message": "Missing product name."})
                issue_count += 1

        # --- Inventory Validation ---
        elif data_type == "inventory":
            qty_col = inv_map.get("quantity")
            qty = row.get(qty_col, 0)
            
            if pd.isna(qty):
                issues.append({"type": "error", "row": row_num, "message": "Missing quantity."})
                error_rows.add(idx)
                issue_count += 1
            else:
                try:
                    qty = float(qty)
                    if qty < 0:
                        issues.append({"type": "error", "row": row_num, "message": "Negative inventory quantity."})
                        error_rows.add(idx)
                        issue_count += 1
                except ValueError:
                    issues.append({"type": "error", "row": row_num, "message": "Quantity is not a number."})
                    error_rows.add(idx)
                    issue_count += 1

        # --- Expenses Validation ---
        elif data_type == "expenses":
            amount_col = inv_map.get("amount")
            amount = row.get(amount_col, 0)
            
            if pd.isna(amount):
                issues.append({"type": "error", "row": row_num, "message": "Missing expense amount."})
                error_rows.add(idx)
                issue_count += 1
            else:
                try:
                    amount = float(amount)
                    if amount < 0:
                        issues.append({"type": "error", "row": row_num, "message": "Negative expense amount."})
                        error_rows.add(idx)
                        issue_count += 1
                except ValueError:
                    issues.append({"type": "error", "row": row_num, "message": "Amount is not a number."})
                    error_rows.add(idx)
                    issue_count += 1
                    
            cat_col = inv_map.get("category")
            if pd.isna(row.get(cat_col)) or str(row.get(cat_col)).strip() == "":
                issues.append({"type": "warning", "row": row_num, "message": "Missing expense category."})
                issue_count += 1

    # Date Validation generic
    date_col = inv_map.get("date")
    if date_col:
        invalid_dates = pd.to_datetime(df[date_col], errors='coerce').isna()
        invalid_count = invalid_dates.sum()
        if invalid_count > 0:
            # We don't log every single one if there are many
            issues.append({"type": "error", "row": "-", "message": f"Found {invalid_count} invalid or missing dates."})
            error_rows.update(df[invalid_dates].index)

    valid_rows = total_rows - len(error_rows)
    
    return {
        "total_rows": total_rows,
        "valid_rows": max(0, valid_rows),
        "issues": issues,
        "duplicates": int(duplicates)
    }


def clean_data(df: pd.DataFrame, data_type: str, mapping: dict) -> pd.DataFrame:
    """Applies automatic cleaning rules based on the mapping."""
    clean_df = df.copy()
    
    # 1. Drop completely empty rows
    clean_df.dropna(how='all', inplace=True)
    
    # 2. Trim string columns
    for col in clean_df.columns:
        if clean_df[col].dtype == 'object':
            clean_df[col] = clean_df[col].astype(str).str.strip()
            
    # 3. Drop duplicates
    clean_df.drop_duplicates(inplace=True)
    
    # 4. Standardize dates
    inv_map = {v: k for k, v in mapping.items()}
    date_col = inv_map.get("date")
    if date_col and date_col in clean_df.columns:
        clean_df[date_col] = pd.to_datetime(clean_df[date_col], errors='coerce').dt.strftime('%Y-%m-%d')
        # Drop rows where date couldn't be parsed
        clean_df.dropna(subset=[date_col], inplace=True)
        
    # 5. Numeric conversions
    numeric_cols = ["quantity", "price", "total_sales", "amount"]
    for nc in numeric_cols:
        col = inv_map.get(nc)
        if col and col in clean_df.columns:
            clean_df[col] = pd.to_numeric(clean_df[col], errors='coerce')
            # Drop rows with NaN in critical numeric columns
            clean_df.dropna(subset=[col], inplace=True)
            
            # Convert negatives to absolute for expenses, or 0 for sales/inventory? Let's just drop negatives.
            clean_df = clean_df[clean_df[col] >= 0]
            
    # 6. Fill missing categories/products with "Unknown"
    cat_col = inv_map.get("category")
    if cat_col and cat_col in clean_df.columns:
        clean_df[cat_col] = clean_df[cat_col].replace('', 'Unknown')
        clean_df[cat_col] = clean_df[cat_col].fillna('Unknown')
        
    prod_col = inv_map.get("product")
    if prod_col and prod_col in clean_df.columns:
        clean_df[prod_col] = clean_df[prod_col].replace('', 'Unknown Product')
        clean_df[prod_col] = clean_df[prod_col].fillna('Unknown Product')
        
    return clean_df
