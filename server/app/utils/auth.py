from typing import Optional
import os
import urllib.request
import json
from jose import jwt, JWTError

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import models

# Clerk Configuration
CLERK_SECRET_KEY = os.environ.get("CLERK_SECRET_KEY")
CLERK_FRONTEND_API = os.environ.get("CLERK_FRONTEND_API", "clerk.your-frontend-api.com")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

# Cache JWKS locally to save network calls
_jwks_cache = None

def get_jwks():
    global _jwks_cache
    if _jwks_cache is None:
        try:
            url = f"https://{CLERK_FRONTEND_API}/.well-known/jwks.json"
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req) as response:
                _jwks_cache = json.loads(response.read().decode())
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to fetch JWKS: {str(e)}")
    return _jwks_cache

def verify_clerk_token(token: str):
    jwks = get_jwks()
    try:
        # We need to extract the exact key used by getting the 'kid' from the unverified header
        unverified_header = jwt.get_unverified_header(token)
        rsa_key = {}
        for key in jwks["keys"]:
            if key["kid"] == unverified_header["kid"]:
                rsa_key = {
                    "kty": key["kty"],
                    "kid": key["kid"],
                    "use": key["use"],
                    "n": key["n"],
                    "e": key["e"]
                }
                break

        if rsa_key:
            payload = jwt.decode(
                token,
                rsa_key,
                algorithms=["RS256"],
                options={"verify_aud": False} 
            )
            return payload
    except JWTError:
        pass
    return None

import httpx
def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    payload = verify_clerk_token(token)
    if not payload:
        raise credentials_exception
        
    clerk_id = payload.get("sub")
    if not clerk_id:
        raise credentials_exception

    # Fast path: Try to see if this user by ID or known email exists
    # If we add a clerk_id column later this would be faster.
    # For now, let's fetch email from Clerk API to ensure we have it.
    
    email = payload.get("email") # check if it's in a custom JWT template
    name = "Clerk User"

    if not email:
        # Fallback to fetching from Clerk API
        if CLERK_SECRET_KEY and "sk_test" not in CLERK_SECRET_KEY:
            try:
                clerk_res = httpx.get(
                    f"https://api.clerk.com/v1/users/{clerk_id}",
                    headers={"Authorization": f"Bearer {CLERK_SECRET_KEY}"}
                )
                if clerk_res.status_code == 200:
                    user_data = clerk_res.json()
                    email_addresses = user_data.get("email_addresses", [])
                    if email_addresses:
                        email = email_addresses[0].get("email_address")
                    name = f"{user_data.get('first_name', '')} {user_data.get('last_name', '')}".strip()
            except Exception:
                pass
                
        # If still no email, use a placeholder based on sub
        if not email:
            email = f"{clerk_id}@clerk.local"

    # Sync user in database
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user:
        user = models.User(
            email=email,
            hashed_password="CLERK_ACCOUNT",
            name=name if name else "Patient",
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    return user
