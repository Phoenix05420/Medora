import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env before importing app.database
env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path)

from app.database import engine, Base
from app.models.models import User, MedicalRecord, Reminder

def init_db():
    print("Initializing Database...")
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully.")

if __name__ == "__main__":
    init_db()
