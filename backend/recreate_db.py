import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from database import engine, Base
import models
from sqlalchemy import text, inspect

# Drop all tables and recreate them
print("Dropping all tables...")

# 모델에 없지만 DB에 남아있을 수 있는 레거시 테이블들을 먼저 안전하게 제거
LEGACY_TABLES = ["applicant_answers", "diagnosis_questions"]

with engine.connect() as conn:
    conn.execute(text("SET FOREIGN_KEY_CHECKS = 0;"))
    conn.commit()

    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()
    for tbl in LEGACY_TABLES:
        if tbl in existing_tables:
            conn.execute(text(f"DROP TABLE IF EXISTS `{tbl}`;"))
            print(f"  레거시 테이블 제거: {tbl}")
    conn.commit()

Base.metadata.drop_all(bind=engine)

with engine.connect() as conn:
    conn.execute(text("SET FOREIGN_KEY_CHECKS = 1;"))
    conn.commit()

print("Recreating tables...")
Base.metadata.create_all(bind=engine)
print("Done. Please run seed.py now.")
