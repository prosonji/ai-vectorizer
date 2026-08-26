"""
User Model
Step 14: is_admin কলাম যোগ করা হলো - এটা দিয়ে বোঝা যাবে কোন ইউজার
Admin Panel এ ঢুকতে পারবে।
"""

from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, DateTime, Boolean

from app.database.db import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    credits = Column(Integer, default=10)
    plan = Column(String, default="free")
    # Step 14: এই ফিল্ড True হলে ইউজার Admin Panel দেখতে/ব্যবহার করতে পারবে
    is_admin = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
