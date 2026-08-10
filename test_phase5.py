"""Test Phase 5: Upload -> Validate -> Clean -> Confirm -> Save."""
import json
import urllib.request
import urllib.error
import time
import sqlite3
import subprocess

BASE = "http://127.0.0.1:8000"

def api(method, path, data=None, token=None):
    url = BASE + path
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())

print("=" * 60)
print("PHASE 5 END-TO-END TEST")
print("=" * 60)

# 1. Register & Login
email = f"val{int(time.time())}@example.com"
print(f"\n1. Register user: {email}")
s, b = api("POST", "/api/auth/register", {"name": "Val Tester", "email": email, "password": "testpassword123"})
assert s == 201, f"Register failed: {b}"
print(f"   OK ({s})")

print("2. Login")
s, b = api("POST", "/api/auth/login", {"email": email, "password": "testpassword123"})
assert s == 200, f"Login failed: {b}"
token = b["access_token"]
print(f"   OK (token received)")

# 2. Setup Business
print("3. Setup business")
s, b = api("POST", "/api/business", {
    "business_name": "Phase5 Store", "business_type": "Retail",
    "location": "Test City", "currency": "INR"
}, token=token)
assert s == 201, f"Business setup failed: {b}"
biz_id = b["id"]
print(f"   OK (business_id={biz_id})")

# 3. Create dirty CSV with known issues
csv = """sale date,product name,qty,price,revenue
2023-01-01,Apple,10,2.00,20.00
2023-01-02,,5,1.50,7.50
invalid-date,Banana,-3,2.00,-6.00
2023-01-04, Orange ,8,3.00,100.00
2023-01-01,Apple,10,2.00,20.00
,,,,
"""
with open("test_dirty.csv", "w") as f:
    f.write(csv)

print("4. Upload dirty CSV")
cmd = f'curl.exe -s -X POST "{BASE}/api/data/upload" -H "Authorization: Bearer {token}" -F "data_type=sales" -F "file=@test_dirty.csv"'
result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
upload_resp = json.loads(result.stdout)
job_id = upload_resp["job_id"]
print(f"   OK (job_id={job_id})")

print("5. Validate")
s, b = api("GET", f"/api/data/validate/{job_id}", token=token)
assert s == 200, f"Validate failed: {b}"
print(f"   Stats: total={b['stats']['total_rows']}, valid={b['stats']['valid_rows']}, dupes={b['stats']['duplicates']}")
print(f"   Issues: {len(b['issues'])}")
for iss in b["issues"]:
    icon = "[ERROR]" if iss["type"] == "error" else "[WARN]"
    print(f"     {icon} Row {iss['row']}: {iss['message']}")
assert len(b["issues"]) > 0, "Expected issues in dirty data"

print("6. Clean")
s, b = api("POST", f"/api/data/clean/{job_id}", token=token)
assert s == 200, f"Clean failed: {b}"
print(f"   Cleaned: total={b['stats']['total_rows']}, valid={b['stats']['valid_rows']}")
print(f"   Remaining issues: {len(b['issues'])}")

print("7. Confirm & Save")
s, b = api("POST", f"/api/data/confirm/{job_id}", token=token)
assert s == 200, f"Confirm failed: {b}"
print(f"   {b['message']} ({b['records_inserted']} records)")

print("8. Verify DB records")
conn = sqlite3.connect("ai_business_twin.db")
c = conn.cursor()
c.execute(f"SELECT date, product, quantity, price, total_sales FROM sales WHERE business_id={biz_id}")
rows = c.fetchall()
print(f"   Found {len(rows)} rows in sales table:")
for r in rows:
    print(f"     {r}")
assert len(rows) > 0, "Expected rows in DB"
conn.close()

print("9. Verify double-save is blocked")
s, b = api("POST", f"/api/data/confirm/{job_id}", token=token)
assert s == 400, f"Expected 400, got {s}"
print(f"   OK (blocked: {b['detail']})")

print("10. Verify cross-business isolation")
email2 = f"other{int(time.time())}@example.com"
api("POST", "/api/auth/register", {"name": "Other", "email": email2, "password": "testpassword123"})
s2, b2 = api("POST", "/api/auth/login", {"email": email2, "password": "testpassword123"})
token2 = b2["access_token"]
api("POST", "/api/business", {"business_name": "Other", "business_type": "X", "location": "X", "currency": "USD"}, token=token2)
s, b = api("GET", f"/api/data/validate/{job_id}", token=token2)
assert s == 404, f"Expected 404 for cross-business access, got {s}"
print(f"   OK (cross-business blocked: {b['detail']})")

# Cleanup
import os
os.remove("test_dirty.csv")

print("\n" + "=" * 60)
print("ALL PHASE 5 TESTS PASSED!")
print("=" * 60)
