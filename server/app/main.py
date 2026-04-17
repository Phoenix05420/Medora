import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env BEFORE any other imports so all modules see the env vars
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from .routes import auth, prescription, summary, reminders, share

app = FastAPI(title="Smart Medical Record System API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(prescription.router)
app.include_router(summary.router)
app.include_router(reminders.router)
app.include_router(share.router)

@app.get("/")
def read_root():
    return {"message": "Smart Medical Record System API is running"}

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
