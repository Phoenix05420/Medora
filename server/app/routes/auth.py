from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import models
from ..utils import auth
from pydantic import BaseModel, EmailStr
from google.oauth2 import id_token
from google.auth.transport import requests
import os

router = APIRouter(prefix="/auth", tags=["auth"])

GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: str
    age: int = None
    gender: str = None
    blood_group: str = None
    location: str = None
    emergency_contact: str = None
    emergency_relation: str = None

class Token(BaseModel):
    access_token: str
    token_type: str

@router.post("/register", response_model=Token)
def register(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_password = auth.get_password_hash(user.password)
    new_user = models.User(
        email=user.email,
        hashed_password=hashed_password,
        name=user.name,
        age=user.age,
        gender=user.gender,
        blood_group=user.blood_group,
        location=user.location,
        emergency_contact=user.emergency_contact,
        emergency_relation=user.emergency_relation
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    access_token = auth.create_access_token(data={"sub": new_user.email})
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == form_data.username).first()
    if not user or not auth.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = auth.create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}

class OAuthRequest(BaseModel):
    token: str

@router.post("/google")
def google_auth(request: OAuthRequest, db: Session = Depends(get_db)):
    try:
        # Verify the ID token from Google
        idinfo = id_token.verify_oauth2_token(request.token, requests.Request(), GOOGLE_CLIENT_ID)

        # ID token is valid. Get the user's Google Account ID from the decoded token.
        email = idinfo['email']
        name = idinfo.get('name', email.split('@')[0])

        # Check if user exists
        user = db.query(models.User).filter(models.User.email == email).first()
        
        if not user:
            # Create a new user with a random password since they use OAuth
            # In a real app, you might want a flag `is_oauth` or similar
            new_user = models.User(
                email=email,
                hashed_password="OAUTH_USER_NO_PASSWORD", # Placeholder
                name=name
            )
            db.add(new_user)
            db.commit()
            db.refresh(new_user)
            user = new_user

        access_token = auth.create_access_token(data={"sub": user.email})
        return {"access_token": access_token, "token_type": "bearer"}
    
    except ValueError:
        # Invalid token
        raise HTTPException(status_code=400, detail="Invalid Google Token")
