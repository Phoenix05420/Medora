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

# Each ALTER TABLE must be its own transaction so one failure doesn't roll back others
columns_to_add = [
    ("medical_records", "diagnoses", "JSONB"),
    ("medical_records", "raw_text", "TEXT"),
    ("medical_records", "notes", "TEXT"),
    ("medical_records", "status", "VARCHAR DEFAULT 'completed'"),
    ("users", "role", "VARCHAR(50) DEFAULT 'patient'"),
]

for table, column, col_type in columns_to_add:
    try:
        with engine.connect() as conn:
            conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {col_type};"))
            conn.commit()
            print(f"  Added '{column}' to '{table}'")
    except Exception as e:
        if "already exists" in str(e) or "DuplicateColumn" in str(e):
            print(f"  Skipped '{column}' on '{table}' (already exists)")
        else:
            print(f"  Error adding '{column}' to '{table}': {e}")

# Also create new tables if they don't exist
table_sqls = [
    """
    CREATE TABLE IF NOT EXISTS hospital_profiles (
        id SERIAL PRIMARY KEY,
        user_id INTEGER REFERENCES users(id),
        specializations JSONB,
        lat VARCHAR,
        lng VARCHAR,
        address VARCHAR
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS emergency_alerts (
        id SERIAL PRIMARY KEY,
        patient_id INTEGER REFERENCES users(id),
        hospital_id INTEGER REFERENCES users(id),
        category VARCHAR,
        lat VARCHAR,
        lng VARCHAR,
        status VARCHAR DEFAULT 'pending',
        created_at TIMESTAMPTZ DEFAULT NOW()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS appointments (
        id SERIAL PRIMARY KEY,
        patient_id INTEGER REFERENCES users(id),
        hospital_id INTEGER REFERENCES users(id),
        appointment_date TIMESTAMPTZ,
        status VARCHAR DEFAULT 'scheduled',
        notes TEXT,
        created_at TIMESTAMPTZ DEFAULT NOW()
    )
    """,
]

for sql in table_sqls:
    try:
        with engine.connect() as conn:
            conn.execute(text(sql))
            conn.commit()
            print(f"  Table ensured OK")
    except Exception as e:
        print(f"  Table error: {e}")

print("\nMigration completed successfully!")
