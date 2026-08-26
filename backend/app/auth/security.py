"""
Security: পাসওয়ার্ড হ্যাশিং + JWT টোকেন (Step 10)
Fix: get_current_user_optional ফাংশনটা আগে এখানে ছিল না, যেটার
কারণে vectorize.py ইমপোর্ট করতে গিয়ে ব্যর্থ হচ্ছিল (deploy ব্যর্থ
হওয়ার আসল কারণ ছিল এটাই)। এখন যোগ করা হলো।

দুইটা মূল কাজ এখানে হয়:
    ১. পাসওয়ার্ড hash করা/যাচাই করা - আসল পাসওয়ার্ড কখনো ডাটাবেজে
       সরাসরি সেভ হয় না, শুধু একমুখী (one-way) hash সেভ হয়
    ২. JWT (JSON Web Token) তৈরি/যাচাই করা - লগইন করার পর ইউজারকে
       একটা "টোকেন" দেওয়া হয়, পরে প্রতিটা request-এ এই টোকেন পাঠিয়ে
       ইউজার প্রমাণ করে সে কে (আবার আবার ইমেইল/পাসওয়ার্ড দেওয়া লাগে না)
"""

import os
from datetime import datetime, timedelta, timezone

import jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.database.db import get_db
from app.models.user import User

# ⚠️ এটা ডেভেলপমেন্টের জন্য একটা সাধারণ secret key।
# আসল প্রোডাকশন অ্যাপে এটা কোডে সরাসরি না লিখে .env ফাইলে/environment
# variable এ রাখা উচিত - কিন্তু আমাদের এই লার্নিং প্রজেক্টের জন্য
# এভাবেই ঠিক আছে।
SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "dev-secret-key-please-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # টোকেন ৭ দিন পর্যন্ত বৈধ থাকবে

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# auto_error=False মানে টোকেন না থাকলে বা ভুল থাকলে FastAPI নিজে থেকেই
# error ছুড়বে না - বরং টোকেনের জায়গায় None পাঠাবে। এটা দরকার কারণ
# get_current_user_optional() ব্যবহার করা endpoint গুলোতে (যেমন
# /vectorize) লগইন ছাড়াও ব্যবহার করা যাবে, শুধু লগইন থাকলে বাড়তি
# সুবিধা (যেমন credit ট্র্যাকিং, history-তে user যুক্ত করা) পাওয়া যাবে।
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login", auto_error=False)


def hash_password(password: str) -> str:
    """প্লেইন পাসওয়ার্ড কে hash করা (এক-মুখী, ফেরত আনা যায় না)"""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """লগইনের সময় দেওয়া পাসওয়ার্ড, সেভ করা hash এর সাথে মিলছে কিনা চেক করা"""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict) -> str:
    """
    ইউজারের জন্য একটা JWT টোকেন তৈরি করা। এই টোকেনের ভিতরে থাকে
    ইউজার আইডি (encoded অবস্থায়) আর একটা মেয়াদ শেষ হওয়ার সময়।
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def _decode_user_from_token(token: str, db: Session) -> User | None:
    """
    টোকেন থেকে ইউজার বের করার common লজিক - get_current_user এবং
    get_current_user_optional দুইটাতেই এটা ব্যবহার হয়, যাতে কোড
    দুইবার লেখা না লাগে।
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            return None
    except jwt.PyJWTError:
        return None

    return db.query(User).filter(User.id == int(user_id)).first()


def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    এটা একটা FastAPI "dependency" - কোনো endpoint এ এটা ব্যবহার করলে
    সেই endpoint শুধু লগইন করা ইউজারই কল করতে পারবে। টোকেন না থাকলে
    বা ভুল থাকলে 401 Unauthorized error দেয় (বাধ্যতামূলক লগইন)।
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="লগইন সেশন সঠিক নয় বা মেয়াদ শেষ হয়ে গেছে, আবার লগইন করো",
    )

    if token is None:
        raise credentials_exception

    user = _decode_user_from_token(token, db)
    if user is None:
        raise credentials_exception
    return user


def get_current_user_optional(
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User | None:
    """
    এটাও একটা FastAPI dependency, কিন্তু get_current_user এর মতো
    বাধ্যতামূলক না - টোকেন না থাকলে বা ভুল থাকলে error না দিয়ে
    শুধু None ফেরত দেয়। এটা এমন endpoint এ ব্যবহার হয় যেগুলো লগইন
    ছাড়া ইউজারও ব্যবহার করতে পারবে (যেমন /vectorize), কিন্তু লগইন
    করা থাকলে অতিরিক্ত কিছু (credit ট্র্যাকিং, ইত্যাদি) করা হয়।
    """
    if token is None:
        return None
    return _decode_user_from_token(token, db)
