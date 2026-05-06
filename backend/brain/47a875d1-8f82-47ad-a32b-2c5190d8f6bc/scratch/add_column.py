from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "mysql+pymysql://root:password@localhost:3306/AISKILL")

engine = create_engine(DATABASE_URL)

def add_column():
    with engine.connect() as conn:
        print("Checking if 'ai_generation_type' column exists...")
        result = conn.execute(text("SHOW COLUMNS FROM questions LIKE 'ai_generation_type'"))
        column_exists = result.fetchone() is not None
        
        if not column_exists:
            print("Adding 'ai_generation_type' column to 'questions' table...")
            conn.execute(text("ALTER TABLE questions ADD COLUMN ai_generation_type VARCHAR(50) NULL AFTER review_status"))
            conn.commit()
            print("Column added successfully.")
        else:
            print("Column 'ai_generation_type' already exists.")

if __name__ == "__main__":
    try:
        add_column()
    except Exception as e:
        print(f"Error: {e}")
