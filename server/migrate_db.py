import os
from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path)

from sqlalchemy import create_engine, text

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    print("NO DATABASE URL FOUND.")
    exit(1)

engine = create_engine(DATABASE_URL)

with engine.connect() as conn:
    print("Adding missing columns to medical_records...")
    try:
        conn.execute(text("ALTER TABLE medical_records ADD COLUMN diagnoses JSON;"))
        print("Added 'diagnoses'")
    except Exception as e:
        print(f"Skipped diagnoses: {e}")

    try:
        conn.execute(text("ALTER TABLE medical_records ADD COLUMN raw_text VARCHAR;"))
        print("Added 'raw_text'")
    except Exception as e:
        print(f"Skipped raw_text: {e}")

    try:
        conn.execute(text("ALTER TABLE medical_records ADD COLUMN notes VARCHAR;"))
        print("Added 'notes'")
    except Exception as e:
        print(f"Skipped notes: {e}")

    conn.commit()
    print("Migration completed.")

