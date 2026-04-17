import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Neon DB typically uses postgresql connection string
# Format: postgresql://[user]:[password]@[host]/[dbname]?sslmode=require
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://user:password@localhost/medical_record_db")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
