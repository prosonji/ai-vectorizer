"""
Security: পাসওয়ার্ড হ্যাশিং + JWT টোকেন
Step 14: get_current_admin_user যোগ করা হলো - এটা দিয়ে শুধু admin
ইউজাররাই কোনো নির্দিষ্ট endpoint ব্যবহার করতে পারবে।
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

SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "dev-secret-key-please-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login", auto_error=False)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def _decode_user_from_token(token: str, db: Session) -> User | None:
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
    if token is None:
        return None
    return _decode_user_from_token(token, db)


def get_current_admin_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Step 14: এটা get_current_user এর উপর ভিত্তি করে বানানো - প্রথমে
    নিশ্চিত করে ইউজার লগইন করা আছে, তারপর চেক করে is_admin=True কিনা।
    যদি admin না হয়, তাহলে 403 Forbidden error দেয় (লগইন থাকলেও
    এই endpoint ব্যবহার করতে পারবে না)।
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="এই পেজ শুধু অ্যাডমিনদের জন্য - তোমার এই অ্যাক্সেস নাই",
        )
    return current_user
