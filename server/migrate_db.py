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
    try:
        print("Ensuring role column exists in users table...")
        conn.execute(text("ALTER TABLE users ADD COLUMN role VARCHAR(50) DEFAULT 'patient';"))
        conn.commit()
        print("Column added successfully!")
    except Exception as e:
        print(f"Error (maybe already exists): {e}")

    try:
        print("Updating existing users to have 'patient' role...")
        conn.execute(text("UPDATE users SET role = 'patient' WHERE role IS NULL;"))
        conn.commit()
    except Exception as e:
        pass

print("Migration completed.")
