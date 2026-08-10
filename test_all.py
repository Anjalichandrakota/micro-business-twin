"""
Comprehensive test suite for AI Business Twin - all phases.
Uses httpx TestClient for in-process testing (no server required).
"""
import os
import sys
import io
import json

# Force UTF-8 output on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# Ensure we use a test database
os.environ["DATABASE_URL"] = "sqlite:///./test_ai_business_twin.db"
os.environ["SECRET_KEY"] = "test-secret-key-for-testing"

# Remove test db if exists
if os.path.exists("test_ai_business_twin.db"):
    os.remove("test_ai_business_twin.db")

from app.database import Base, engine, get_db
from main import app
from fastapi.testclient import TestClient

# Create all tables
Base.metadata.create_all(bind=engine)

client = TestClient(app)

PASSED = 0
FAILED = 0
ERRORS = []

def test(name, condition, detail=""):
    global PASSED, FAILED
    if condition:
        PASSED += 1
        print(f"  [PASS] {name}")
    else:
        FAILED += 1
        ERRORS.append(f"{name}: {detail}")
        print(f"  [FAIL] {name} -- {detail}")

# ============================================================
print("\n" + "=" * 60)
print("AI BUSINESS TWIN -- COMPREHENSIVE TEST SUITE")
print("=" * 60)

# --- Phase 1: Landing Page ---
print("\n[Phase 1] Landing Page")
r = client.get("/")
test("Landing page loads", r.status_code == 200)
test("Landing page has title", "AI Business Twin" in r.text)
test("Landing page has CTA", "Get Started" in r.text)

# --- Phase 2: Authentication ---
print("\n[Phase 2] Authentication")
EMAIL = "test@example.com"
PASSWORD = "securepass123"

r = client.post("/api/auth/register", json={"name": "Test User", "email": EMAIL, "password": PASSWORD})
test("Register user", r.status_code == 201, r.text)

r = client.post("/api/auth/register", json={"name": "Test User", "email": EMAIL, "password": PASSWORD})
test("Reject duplicate email", r.status_code == 409)

r = client.post("/api/auth/login", json={"email": EMAIL, "password": PASSWORD})
test("Login user", r.status_code == 200)
TOKEN = r.json()["access_token"]
test("Received JWT token", len(TOKEN) > 20)

r = client.post("/api/auth/login", json={"email": EMAIL, "password": "wrongpass"})
test("Reject bad password", r.status_code == 401)

headers = {"Authorization": f"Bearer {TOKEN}"}
r = client.get("/api/auth/me", headers=headers)
test("Get current user", r.status_code == 200)
test("User email matches", r.json()["email"] == EMAIL)

r = client.get("/api/auth/me", headers={"Authorization": "Bearer invalid_token"})
test("Reject invalid token", r.status_code in [401, 403])

# --- Phase 3: Business Setup ---
print("\n[Phase 3] Business Setup")
r = client.post("/api/business", json={
    "business_name": "Test Store", "business_type": "Retail",
    "location": "Test City", "currency": "INR"
}, headers=headers)
test("Create business", r.status_code == 201, r.text)
BIZ_ID = r.json()["id"]
test("Business has ID", BIZ_ID > 0)

r = client.post("/api/business", json={
    "business_name": "Another Store", "business_type": "Retail",
    "location": "Elsewhere", "currency": "USD"
}, headers=headers)
test("Reject duplicate business", r.status_code in [409, 422, 500])

r = client.get("/api/business", headers=headers)
test("Get business", r.status_code == 200)
test("Business name matches", r.json()["business_name"] == "Test Store")

# --- Phase 4: CSV/Excel Upload ---
print("\n[Phase 4] File Upload")

csv_content = """sale date,product name,qty,price,revenue
2024-01-01,Apple,10,2.50,25.00
2024-01-02,Banana,5,1.50,7.50
2024-01-03,Orange,8,3.00,24.00
2024-01-04,Apple,12,2.50,30.00
2024-01-05,Banana,15,1.50,22.50
2024-01-06,Mango,6,4.00,24.00
2024-01-07,Apple,20,2.50,50.00
2024-01-08,Orange,10,3.00,30.00
2024-01-09,Banana,8,1.50,12.00
2024-01-10,Mango,4,4.00,16.00
"""
csv_file = io.BytesIO(csv_content.encode())

r = client.post("/api/data/upload",
    data={"data_type": "sales"},
    files={"file": ("test_sales.csv", csv_file, "text/csv")},
    headers=headers)
test("Upload CSV", r.status_code == 200, r.text)
SALES_JOB_ID = r.json()["job_id"]
test("Got job ID", SALES_JOB_ID > 0)

r = client.post("/api/data/upload",
    data={"data_type": "sales"},
    files={"file": ("test.csv", io.BytesIO(b"x"), "text/csv")})
test("Reject upload without auth", r.status_code in [401, 403])

r = client.post("/api/data/upload",
    data={"data_type": "sales"},
    files={"file": ("test.txt", io.BytesIO(b"x"), "text/plain")},
    headers=headers)
test("Reject non-CSV/Excel", r.status_code == 400)

# --- Phase 5: Validation + Cleaning ---
print("\n[Phase 5] Validation & Cleaning")

r = client.get(f"/api/data/validate/{SALES_JOB_ID}", headers=headers)
test("Validate uploaded data", r.status_code == 200, r.text)
val = r.json()
test("Has mapping", len(val.get("mapping", {})) > 0)
test("Has stats", "total_rows" in val.get("stats", {}))
test("Total rows = 10", val["stats"]["total_rows"] == 10)

dirty_csv = """sale date,product name,qty,price,revenue
2024-01-01,Apple,10,2.00,20.00
2024-01-02,,5,1.50,7.50
invalid-date,Banana,-3,2.00,-6.00
2024-01-04, Orange ,8,3.00,100.00
2024-01-01,Apple,10,2.00,20.00
,,,,
"""
r = client.post("/api/data/upload",
    data={"data_type": "sales"},
    files={"file": ("dirty.csv", io.BytesIO(dirty_csv.encode()), "text/csv")},
    headers=headers)
DIRTY_JOB = r.json()["job_id"]

r = client.get(f"/api/data/validate/{DIRTY_JOB}", headers=headers)
test("Dirty data has issues", len(r.json()["issues"]) > 0)

r = client.post(f"/api/data/clean/{DIRTY_JOB}", headers=headers)
test("Clean dirty data", r.status_code == 200, r.text)

# Confirm clean data
r = client.post(f"/api/data/confirm/{SALES_JOB_ID}", headers=headers)
test("Confirm & save data", r.status_code == 200, r.text)
test("Records inserted", r.json()["records_inserted"] == 10)

r = client.post(f"/api/data/confirm/{SALES_JOB_ID}", headers=headers)
test("Reject double save", r.status_code == 400)

# --- Upload inventory & expenses ---
print("\n[Phase 4b] Inventory & Expense Upload")

inv_csv = """product,sku,quantity,location
Apple,APL001,50,Main
Banana,BAN001,8,Main
Orange,ORG001,3,Main
Mango,MNG001,25,Main
"""
r = client.post("/api/data/upload",
    data={"data_type": "inventory"},
    files={"file": ("inv.csv", io.BytesIO(inv_csv.encode()), "text/csv")},
    headers=headers)
INV_JOB = r.json()["job_id"]

r = client.get(f"/api/data/validate/{INV_JOB}", headers=headers)
test("Validate inventory", r.status_code == 200)

r = client.post(f"/api/data/confirm/{INV_JOB}", headers=headers)
test("Save inventory", r.status_code == 200, r.text)

exp_csv = """date,category,amount,description
2024-01-01,Rent,5000,Monthly rent
2024-01-01,Utilities,800,Electricity
2024-01-05,Transport,500,Delivery
2024-01-10,Rent,5000,Monthly rent
2024-01-15,Supplies,1200,Packaging materials
"""
r = client.post("/api/data/upload",
    data={"data_type": "expenses"},
    files={"file": ("exp.csv", io.BytesIO(exp_csv.encode()), "text/csv")},
    headers=headers)
EXP_JOB = r.json()["job_id"]

r = client.get(f"/api/data/validate/{EXP_JOB}", headers=headers)
test("Validate expenses", r.status_code == 200)

r = client.post(f"/api/data/confirm/{EXP_JOB}", headers=headers)
test("Save expenses", r.status_code == 200, r.text)

# --- Phase 6: Analytics Engine ---
print("\n[Phase 6] Analytics Engine")

r = client.get("/api/analytics", headers=headers)
test("Get analytics", r.status_code == 200, r.text)
analytics = r.json()

test("Has KPIs", "kpis" in analytics)
test("Has sales trends", "sales_trends" in analytics)
test("Has top products", "top_products" in analytics)
test("Has inventory summary", "inventory_summary" in analytics)
test("Has category breakdown", "category_breakdown" in analytics)
test("Has alerts", "alerts" in analytics)
test("Has business info", "business" in analytics)
test("Revenue > 0", analytics["kpis"]["total_revenue"] > 0)
test("Expenses > 0", analytics["kpis"]["total_expenses"] > 0)
test("Profit calculated", analytics["kpis"]["gross_profit"] is not None)
test("Stock counted", analytics["kpis"]["total_stock"] > 0)
test("Products counted", analytics["kpis"]["unique_products"] > 0)

r = client.get("/api/analytics?date_from=2024-01-01&date_to=2024-01-05", headers=headers)
test("Analytics with date filter", r.status_code == 200)

r = client.get("/api/analytics/products", headers=headers)
test("Get product list", r.status_code == 200)
test("Products returned", len(r.json()["products"]) > 0)

# --- Phase 7: Dashboard ---
print("\n[Phase 7] Dashboard")

r = client.get("/dashboard")
test("Dashboard page loads", r.status_code == 200)
test("Dashboard has KPI grid", "kpi-grid" in r.text)
test("Dashboard has charts", "revenue-chart" in r.text)

# --- Phase 8: AI Assistant ---
print("\n[Phase 8] AI Assistant")

r = client.get("/assistant")
test("Assistant page loads", r.status_code == 200)

r = client.post("/api/assistant", json={
    "question": "How is my business doing?",
    "history": []
}, headers=headers)
test("AI assistant responds", r.status_code == 200, r.text)
test("Has response text", len(r.json().get("response", "")) > 0)
test("Has data flag", "has_data" in r.json())

r = client.post("/api/assistant", json={
    "question": "What are my top products?",
    "history": [
        {"role": "user", "content": "How is my business?"},
        {"role": "assistant", "content": "Your business is doing well."}
    ]
}, headers=headers)
test("Assistant with history", r.status_code == 200)

# --- Phase 9: What-If Engine ---
print("\n[Phase 9] What-If Engine")

r = client.get("/whatif")
test("What-If page loads", r.status_code == 200)

r = client.post("/api/analytics/whatif", json={
    "type": "price_change",
    "change_percent": 10
}, headers=headers)
test("Price change scenario", r.status_code == 200, r.text)
wi = r.json()
test("Has current metrics", "current" in wi)
test("Has projected metrics", "projected" in wi)
test("Has impact", "impact" in wi)
test("Has explanation", len(wi.get("explanation", "")) > 0)
test("Revenue changed", wi["projected"]["revenue"] != wi["current"]["revenue"])

r = client.post("/api/analytics/whatif", json={
    "type": "discount",
    "change_percent": 15
}, headers=headers)
test("Discount scenario", r.status_code == 200)

r = client.post("/api/analytics/whatif", json={
    "type": "expense_change",
    "change_percent": -20
}, headers=headers)
test("Expense reduction scenario", r.status_code == 200)
test("Expenses decreased", r.json()["projected"]["expenses"] < r.json()["current"]["expenses"])

r = client.post("/api/analytics/whatif", json={
    "type": "quantity_change",
    "product": "Apple",
    "change_percent": 25
}, headers=headers)
test("Product-specific scenario", r.status_code == 200)

# --- Phase 10: AI + Analytics Integration ---
print("\n[Phase 10] AI + Analytics Integration")

r = client.post("/api/assistant", json={
    "question": "Explain my revenue trend and profit margin",
}, headers=headers)
test("AI explains metrics", r.status_code == 200)
test("Response has content", len(r.json()["response"]) > 20)

r = client.post("/api/assistant", json={
    "question": "What products should I focus on?",
}, headers=headers)
test("AI gives product advice", r.status_code == 200)

# --- Phase 11: Security & Isolation ---
print("\n[Phase 11] Security & Isolation")

EMAIL2 = "other@example.com"
r = client.post("/api/auth/register", json={"name": "Other User", "email": EMAIL2, "password": "otherpass123"})
test("Register second user", r.status_code == 201)

r = client.post("/api/auth/login", json={"email": EMAIL2, "password": "otherpass123"})
TOKEN2 = r.json()["access_token"]
headers2 = {"Authorization": f"Bearer {TOKEN2}"}

r = client.post("/api/business", json={
    "business_name": "Other Biz", "business_type": "Food",
    "location": "Elsewhere", "currency": "USD"
}, headers=headers2)
test("Create second business", r.status_code == 201)

r = client.get(f"/api/data/validate/{SALES_JOB_ID}", headers=headers2)
test("Block cross-biz data access", r.status_code == 404)

r = client.post(f"/api/data/clean/{SALES_JOB_ID}", headers=headers2)
test("Block cross-biz clean", r.status_code == 404)

r = client.post(f"/api/data/confirm/{SALES_JOB_ID}", headers=headers2)
test("Block cross-biz confirm", r.status_code in [400, 404])

r = client.get("/api/analytics", headers=headers2)
test("Second user analytics empty", r.status_code == 200)
test("Second user has no sales", r.json()["has_sales"] == False)

r = client.put(f"/api/business/{BIZ_ID}", json={
    "business_name": "Hacked Name", "business_type": "Hack",
    "location": "Hackville", "currency": "XX"
}, headers=headers2)
test("Block cross-biz update", r.status_code == 403)

# No auth tests
r = client.get("/api/analytics")
test("Analytics requires auth", r.status_code in [401, 403])

r = client.post("/api/assistant", json={"question": "test"})
test("Assistant requires auth", r.status_code in [401, 403])

r = client.post("/api/analytics/whatif", json={"type": "price_change", "change_percent": 10})
test("What-if requires auth", r.status_code in [401, 403])

# --- Phase 12: All Pages Load ---
print("\n[Phase 12] All Pages & Error Handling")

for page in ["/", "/login", "/register", "/setup", "/dashboard", "/upload", "/validate", "/assistant", "/whatif"]:
    r = client.get(page)
    test(f"Page {page} loads", r.status_code == 200, f"Status: {r.status_code}")

r = client.get("/api/data/validate/99999", headers=headers)
test("404 for nonexistent job", r.status_code == 404)

r = client.post("/api/analytics/whatif", json={"type": ""}, headers=headers)
test("Reject empty scenario type", r.status_code == 400)

# ============================================================
print("\n" + "=" * 60)
print(f"RESULTS: {PASSED} passed, {FAILED} failed out of {PASSED + FAILED} tests")
print("=" * 60)

if ERRORS:
    print("\nFailed tests:")
    for e in ERRORS:
        print(f"  [FAIL] {e}")

# Cleanup
try:
    if os.path.exists("test_ai_business_twin.db"):
        os.remove("test_ai_business_twin.db")
except:
    pass

if FAILED > 0:
    print(f"\n{FAILED} test(s) FAILED.")
    sys.exit(1)
else:
    print("\nALL TESTS PASSED!")
    sys.exit(0)
