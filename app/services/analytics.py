"""
Analytics Engine — calculates KPIs, trends, and insights from validated business data.
"""

import pandas as pd
import numpy as np
from sqlalchemy.orm import Session
from app.models.data import Sales, Inventory, Expenses
from app.models.business import Business


def get_sales_dataframe(db: Session, business_id: int) -> pd.DataFrame:
    """Load all sales rows for a business into a DataFrame."""
    rows = db.query(Sales).filter(Sales.business_id == business_id).all()
    if not rows:
        return pd.DataFrame()
    data = [{
        "date": r.date, "product": r.product,
        "quantity": r.quantity, "price": r.price,
        "total_sales": r.total_sales
    } for r in rows]
    df = pd.DataFrame(data)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    return df


def get_inventory_dataframe(db: Session, business_id: int) -> pd.DataFrame:
    """Load all inventory rows for a business into a DataFrame."""
    rows = db.query(Inventory).filter(Inventory.business_id == business_id).all()
    if not rows:
        return pd.DataFrame()
    data = [{
        "product": r.product, "sku": r.sku,
        "quantity": r.quantity, "location": r.location
    } for r in rows]
    return pd.DataFrame(data)


def get_expenses_dataframe(db: Session, business_id: int) -> pd.DataFrame:
    """Load all expenses rows for a business into a DataFrame."""
    rows = db.query(Expenses).filter(Expenses.business_id == business_id).all()
    if not rows:
        return pd.DataFrame()
    data = [{
        "date": r.date, "category": r.category,
        "amount": r.amount, "description": r.description
    } for r in rows]
    df = pd.DataFrame(data)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    return df


def compute_analytics(db: Session, business_id: int, date_from: str = None, date_to: str = None) -> dict:
    """Compute comprehensive business analytics."""
    sales_df = get_sales_dataframe(db, business_id)
    inventory_df = get_inventory_dataframe(db, business_id)
    expenses_df = get_expenses_dataframe(db, business_id)

    # Apply date filters
    if not sales_df.empty and date_from:
        sales_df = sales_df[sales_df["date"] >= pd.to_datetime(date_from)]
    if not sales_df.empty and date_to:
        sales_df = sales_df[sales_df["date"] <= pd.to_datetime(date_to)]
    if not expenses_df.empty and date_from:
        expenses_df = expenses_df[expenses_df["date"] >= pd.to_datetime(date_from)]
    if not expenses_df.empty and date_to:
        expenses_df = expenses_df[expenses_df["date"] <= pd.to_datetime(date_to)]

    result = {
        "kpis": _compute_kpis(sales_df, expenses_df, inventory_df),
        "sales_trends": _compute_sales_trends(sales_df),
        "top_products": _compute_top_products(sales_df),
        "bottom_products": _compute_bottom_products(sales_df),
        "category_breakdown": _compute_categories(expenses_df),
        "inventory_summary": _compute_inventory_summary(inventory_df),
        "daily_revenue": _compute_daily_revenue(sales_df),
        "monthly_revenue": _compute_monthly_revenue(sales_df),
        "alerts": _compute_alerts(sales_df, inventory_df, expenses_df),
        "has_sales": not sales_df.empty,
        "has_inventory": not inventory_df.empty,
        "has_expenses": not expenses_df.empty,
    }
    return result


def _safe_float(val):
    """Convert numpy/pandas values to native Python float."""
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return 0.0
    return float(val)


def _compute_kpis(sales_df, expenses_df, inventory_df) -> dict:
    """Calculate key performance indicators."""
    total_revenue = _safe_float(sales_df["total_sales"].sum()) if not sales_df.empty else 0
    total_orders = len(sales_df) if not sales_df.empty else 0
    total_quantity = _safe_float(sales_df["quantity"].sum()) if not sales_df.empty else 0
    total_expenses = _safe_float(expenses_df["amount"].sum()) if not expenses_df.empty else 0
    gross_profit = total_revenue - total_expenses
    profit_margin = (gross_profit / total_revenue * 100) if total_revenue > 0 else 0
    avg_order_value = total_revenue / total_orders if total_orders > 0 else 0
    unique_products = sales_df["product"].nunique() if not sales_df.empty else 0
    total_stock = _safe_float(inventory_df["quantity"].sum()) if not inventory_df.empty else 0

    # Trends: compare first half vs second half of data
    revenue_trend = 0
    if not sales_df.empty and len(sales_df) > 1:
        sorted_df = sales_df.sort_values("date")
        mid = len(sorted_df) // 2
        first_half = _safe_float(sorted_df.iloc[:mid]["total_sales"].sum())
        second_half = _safe_float(sorted_df.iloc[mid:]["total_sales"].sum())
        if first_half > 0:
            revenue_trend = ((second_half - first_half) / first_half) * 100

    return {
        "total_revenue": round(total_revenue, 2),
        "total_orders": total_orders,
        "total_quantity": round(total_quantity, 2),
        "total_expenses": round(total_expenses, 2),
        "gross_profit": round(gross_profit, 2),
        "profit_margin": round(profit_margin, 1),
        "avg_order_value": round(avg_order_value, 2),
        "unique_products": unique_products,
        "total_stock": round(total_stock, 2),
        "revenue_trend": round(revenue_trend, 1),
    }


def _compute_sales_trends(sales_df) -> list:
    """Weekly sales trend data."""
    if sales_df.empty:
        return []
    df = sales_df.copy()
    df = df.dropna(subset=["date"])
    if df.empty:
        return []
    df["week"] = df["date"].dt.isocalendar().week.astype(int)
    df["year"] = df["date"].dt.year
    weekly = df.groupby(["year", "week"]).agg(
        revenue=("total_sales", "sum"),
        orders=("quantity", "count")
    ).reset_index().sort_values(["year", "week"])

    return [
        {"week": f"W{int(r['week'])}", "year": int(r["year"]),
         "revenue": round(float(r["revenue"]), 2),
         "orders": int(r["orders"])}
        for _, r in weekly.iterrows()
    ][-12:]  # Last 12 weeks


def _compute_top_products(sales_df, n=10) -> list:
    """Top N products by revenue."""
    if sales_df.empty:
        return []
    product_rev = sales_df.groupby("product").agg(
        revenue=("total_sales", "sum"),
        quantity=("quantity", "sum"),
        orders=("product", "count")
    ).reset_index().sort_values("revenue", ascending=False).head(n)

    return [
        {"product": r["product"], "revenue": round(float(r["revenue"]), 2),
         "quantity": round(float(r["quantity"]), 2), "orders": int(r["orders"])}
        for _, r in product_rev.iterrows()
    ]


def _compute_bottom_products(sales_df, n=5) -> list:
    """Bottom N products by revenue."""
    if sales_df.empty:
        return []
    product_rev = sales_df.groupby("product").agg(
        revenue=("total_sales", "sum"),
        quantity=("quantity", "sum")
    ).reset_index().sort_values("revenue", ascending=True).head(n)

    return [
        {"product": r["product"], "revenue": round(float(r["revenue"]), 2),
         "quantity": round(float(r["quantity"]), 2)}
        for _, r in product_rev.iterrows()
    ]


def _compute_categories(expenses_df) -> list:
    """Expense breakdown by category."""
    if expenses_df.empty:
        return []
    cat = expenses_df.groupby("category").agg(
        total=("amount", "sum"),
        count=("amount", "count")
    ).reset_index().sort_values("total", ascending=False)

    return [
        {"category": r["category"], "total": round(float(r["total"]), 2),
         "count": int(r["count"])}
        for _, r in cat.iterrows()
    ]


def _compute_inventory_summary(inventory_df) -> list:
    """Inventory summary per product."""
    if inventory_df.empty:
        return []
    inv = inventory_df.groupby("product").agg(
        total_quantity=("quantity", "sum"),
        locations=("location", "nunique")
    ).reset_index().sort_values("total_quantity", ascending=True)

    return [
        {"product": r["product"],
         "total_quantity": round(float(r["total_quantity"]), 2),
         "locations": int(r["locations"])}
        for _, r in inv.iterrows()
    ][:20]


def _compute_daily_revenue(sales_df) -> list:
    """Daily revenue for charts."""
    if sales_df.empty:
        return []
    df = sales_df.dropna(subset=["date"]).copy()
    if df.empty:
        return []
    daily = df.groupby(df["date"].dt.strftime("%Y-%m-%d")).agg(
        revenue=("total_sales", "sum"),
        orders=("product", "count")
    ).reset_index()
    daily.columns = ["date", "revenue", "orders"]
    daily = daily.sort_values("date")

    return [
        {"date": r["date"], "revenue": round(float(r["revenue"]), 2),
         "orders": int(r["orders"])}
        for _, r in daily.iterrows()
    ][-60:]  # Last 60 days


def _compute_monthly_revenue(sales_df) -> list:
    """Monthly revenue for charts."""
    if sales_df.empty:
        return []
    df = sales_df.dropna(subset=["date"]).copy()
    if df.empty:
        return []
    monthly = df.groupby(df["date"].dt.strftime("%Y-%m")).agg(
        revenue=("total_sales", "sum"),
        orders=("product", "count")
    ).reset_index()
    monthly.columns = ["month", "revenue", "orders"]
    monthly = monthly.sort_values("month")

    return [
        {"month": r["month"], "revenue": round(float(r["revenue"]), 2),
         "orders": int(r["orders"])}
        for _, r in monthly.iterrows()
    ][-12:]


def _compute_alerts(sales_df, inventory_df, expenses_df) -> list:
    """Generate business alerts based on data patterns."""
    alerts = []

    # Low stock alerts
    if not inventory_df.empty:
        low_stock = inventory_df[inventory_df["quantity"] <= 10]
        for _, row in low_stock.iterrows():
            alerts.append({
                "type": "warning",
                "title": "Low Stock",
                "message": f"{row['product']} has only {int(row['quantity'])} units remaining."
            })

    # Zero-stock alerts
    if not inventory_df.empty:
        zero_stock = inventory_df[inventory_df["quantity"] <= 0]
        for _, row in zero_stock.iterrows():
            alerts.append({
                "type": "error",
                "title": "Out of Stock",
                "message": f"{row['product']} is out of stock!"
            })

    # High expenses alert
    if not expenses_df.empty and not sales_df.empty:
        total_rev = sales_df["total_sales"].sum()
        total_exp = expenses_df["amount"].sum()
        if total_rev > 0 and total_exp / total_rev > 0.8:
            alerts.append({
                "type": "warning",
                "title": "High Expense Ratio",
                "message": f"Expenses are {round(total_exp/total_rev*100, 1)}% of revenue. Review cost optimization."
            })

    return alerts[:10]  # Cap at 10 alerts


def compute_whatif(db: Session, business_id: int, scenario: dict) -> dict:
    """
    What-If scenario engine.
    scenario = {
        "type": "price_change" | "quantity_change" | "expense_change" | "discount",
        "product": "...",          # optional, product filter
        "change_percent": 10.0,    # percentage change
        "change_absolute": 5.0,    # absolute change (alternative)
    }
    """
    sales_df = get_sales_dataframe(db, business_id)
    expenses_df = get_expenses_dataframe(db, business_id)
    inventory_df = get_inventory_dataframe(db, business_id)

    scenario_type = scenario.get("type", "price_change")
    product_filter = scenario.get("product")
    change_pct = scenario.get("change_percent", 0)
    change_abs = scenario.get("change_absolute", 0)

    # Current metrics
    current_revenue = _safe_float(sales_df["total_sales"].sum()) if not sales_df.empty else 0
    current_expenses = _safe_float(expenses_df["amount"].sum()) if not expenses_df.empty else 0
    current_profit = current_revenue - current_expenses
    current_quantity = _safe_float(sales_df["quantity"].sum()) if not sales_df.empty else 0

    # Apply scenario
    projected_revenue = current_revenue
    projected_expenses = current_expenses
    projected_quantity = current_quantity
    explanation = ""

    if scenario_type == "price_change":
        if not sales_df.empty:
            if product_filter:
                mask = sales_df["product"] == product_filter
                affected_rev = _safe_float(sales_df.loc[mask, "total_sales"].sum())
                delta = affected_rev * (change_pct / 100)
                projected_revenue = current_revenue + delta
                explanation = f"Changing price of '{product_filter}' by {change_pct:+.1f}% would affect ₹{abs(delta):,.2f} in revenue."
            else:
                delta = current_revenue * (change_pct / 100)
                projected_revenue = current_revenue + delta
                explanation = f"Changing all prices by {change_pct:+.1f}% would change revenue by ₹{abs(delta):,.2f}."

    elif scenario_type == "quantity_change":
        if not sales_df.empty:
            if product_filter:
                mask = sales_df["product"] == product_filter
                avg_price = _safe_float(sales_df.loc[mask, "price"].mean()) if mask.any() else 0
                qty_change = change_abs if change_abs else (current_quantity * change_pct / 100)
                delta = qty_change * avg_price
                projected_revenue = current_revenue + delta
                projected_quantity = current_quantity + qty_change
                explanation = f"Selling {qty_change:+.0f} more units of '{product_filter}' at avg price would change revenue by ₹{abs(delta):,.2f}."
            else:
                qty_change = current_quantity * (change_pct / 100)
                avg_price = current_revenue / current_quantity if current_quantity > 0 else 0
                delta = qty_change * avg_price
                projected_revenue = current_revenue + delta
                projected_quantity = current_quantity + qty_change
                explanation = f"Changing total sales volume by {change_pct:+.1f}% would change revenue by ₹{abs(delta):,.2f}."

    elif scenario_type == "expense_change":
        delta = current_expenses * (change_pct / 100) if change_pct else change_abs
        projected_expenses = current_expenses + delta
        explanation = f"Changing expenses by {change_pct:+.1f}% would change total costs by ₹{abs(delta):,.2f}."

    elif scenario_type == "discount":
        discount_pct = abs(change_pct)
        # Simple demand elasticity model: 10% discount => ~15% more quantity
        elasticity = 1.5
        qty_increase_pct = discount_pct * elasticity
        new_price_factor = 1 - (discount_pct / 100)
        new_qty_factor = 1 + (qty_increase_pct / 100)
        projected_revenue = current_revenue * new_price_factor * new_qty_factor
        projected_quantity = current_quantity * new_qty_factor
        explanation = f"A {discount_pct:.1f}% discount could increase volume by ~{qty_increase_pct:.1f}% (elasticity estimate). Net revenue impact: ₹{projected_revenue - current_revenue:+,.2f}."

    projected_profit = projected_revenue - projected_expenses
    revenue_change = projected_revenue - current_revenue
    profit_change = projected_profit - current_profit

    return {
        "scenario": scenario,
        "current": {
            "revenue": round(current_revenue, 2),
            "expenses": round(current_expenses, 2),
            "profit": round(current_profit, 2),
            "quantity": round(current_quantity, 2),
        },
        "projected": {
            "revenue": round(projected_revenue, 2),
            "expenses": round(projected_expenses, 2),
            "profit": round(projected_profit, 2),
            "quantity": round(projected_quantity, 2),
        },
        "impact": {
            "revenue_change": round(revenue_change, 2),
            "profit_change": round(profit_change, 2),
            "revenue_change_pct": round(revenue_change / current_revenue * 100, 1) if current_revenue > 0 else 0,
            "profit_change_pct": round(profit_change / current_profit * 100, 1) if current_profit != 0 else 0,
        },
        "explanation": explanation,
        "disclaimer": "These are estimates based on historical data and simplified models. Actual results may vary."
    }
