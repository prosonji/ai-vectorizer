"""
Auth API (Step 10)
Step 12: Security - login/register এ rate limiting যোগ করা হলো, যাতে
কেউ script দিয়ে বারবার পাসওয়ার্ড অনুমান করার চেষ্টা (brute-force
attack) করতে না পারে।

তিনটা endpoint:
    POST /register  -> নতুন অ্যাকাউন্ট বানানো
    POST /login      -> লগইন করে টোকেন পাওয়া
    GET  /me          -> এখন কে লগইন করা আছে, তার তথ্য (টোকেন লাগবে)
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.database.db import get_db
from app.models.user import User
from app.auth.security import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user,
)
from app.rate_limiter import limiter

router = APIRouter()


# ---- Request এর গঠন (ইউজার কী কী পাঠাবে) ----

class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


def _user_to_dict(user: User) -> dict:
    """User object কে JSON এ পাঠানোর মতো dict এ রূপান্তর করা (পাসওয়ার্ড বাদে)"""
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "credits": user.credits,
        "plan": user.plan,
    }


@router.post("/register")
@limiter.limit("5/minute")
def register(request: Request, payload: RegisterRequest, db: Session = Depends(get_db)):
    """
    নতুন অ্যাকাউন্ট তৈরি করা। একই ইমেইল দিয়ে আগে থেকে অ্যাকাউন্ট
    থাকলে error দেওয়া হয়। সফল হলে সাথে সাথেই একটা লগইন টোকেনও
    ফেরত দেওয়া হয় (আলাদা করে আবার লগইন করা লাগে না)।
    """
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail="এই ইমেইল দিয়ে আগেই একটা অ্যাকাউন্ট আছে, লগইন করো",
        )

    user = User(
        name=payload.name,
        email=payload.email,
        hashed_password=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token({"sub": str(user.id)})

    return {
        "status": "ok",
        "message": "অ্যাকাউন্ট সফলভাবে তৈরি হয়েছে",
        "access_token": token,
        "token_type": "bearer",
        "user": _user_to_dict(user),
    }


@router.post("/login")
@limiter.limit("5/minute")
def login(request: Request, payload: LoginRequest, db: Session = Depends(get_db)):
    """
    ইমেইল-পাসওয়ার্ড দিয়ে লগইন করা। সঠিক হলে একটা JWT টোকেন ফেরত
    দেওয়া হয় - frontend এই টোকেনটা সেভ রাখবে, পরের প্রতিটা request
    এর সাথে এটা পাঠাবে।
    """
    user = db.query(User).filter(User.email == payload.email).first()

    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="ইমেইল বা পাসওয়ার্ড ভুল")

    token = create_access_token({"sub": str(user.id)})

    return {
        "status": "ok",
        "message": "লগইন সফল হয়েছে",
        "access_token": token,
        "token_type": "bearer",
        "user": _user_to_dict(user),
    }


@router.get("/me")
def me(current_user: User = Depends(get_current_user)):
    """
    এখন কে লগইন করা আছে তার তথ্য ফেরত দেয়। এটা কল করার সময় টোকেন
    না পাঠালে বা ভুল টোকেন পাঠালে 401 (Unauthorized) error আসবে।
    """
    return _user_to_dict(current_user)
