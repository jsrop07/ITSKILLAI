import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

print("[1] Importing database module...")
try:
    from database import engine, SessionLocal, Base
    print("[1] OK")
except Exception as e:
    print(f"[1] FAIL: {e}")
    sys.exit(1)

print("[2] Testing DB connection...")
try:
    from sqlalchemy import text
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        print(f"[2] OK - result: {result.fetchone()}")
except Exception as e:
    print(f"[2] FAIL: {e}")
    sys.exit(1)

print("[3] Importing models...")
try:
    import models
    print(f"[3] OK - tables: {list(Base.metadata.tables.keys())}")
except Exception as e:
    print(f"[3] FAIL: {e}")
    sys.exit(1)

print("[4] Creating tables...")
try:
    Base.metadata.create_all(bind=engine)
    print("[4] OK")
except Exception as e:
    print(f"[4] FAIL: {e}")
    sys.exit(1)

print("[5] Checking admin account...")
try:
    db = SessionLocal()
    from models import Admin
    admin = db.query(Admin).first()
    if admin:
        print(f"[5] OK - admin found: {admin.email}")
    else:
        print("[5] WARNING - No admin found. Run seed.py")
    db.close()
except Exception as e:
    print(f"[5] FAIL: {e}")

print("[6] Checking routers...")
try:
    from routers import auth, dashboard, applicants, diagnoses, questions, records, exam, page_contents
    print("[6] OK - all routers imported")
except Exception as e:
    print(f"[6] FAIL: {e}")

print("")
print("=== Diagnosis Complete ===")
