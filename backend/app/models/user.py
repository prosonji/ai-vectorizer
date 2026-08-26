"""
User Model (Step 10)

এটা ডাটাবেজের "users" টেবিলের গঠন বর্ণনা করে - এখানে প্রতিটা
Column একটা টেবিলের কলাম হয়ে যাবে।
"""

from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, DateTime

from app.database.db import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    # email অবশ্যই ইউনিক হতে হবে - দুইজন ইউজার একই ইমেইল দিয়ে
    # অ্যাকাউন্ট বানাতে পারবে না
    email = Column(String, unique=True, index=True, nullable=False)
    # আসল পাসওয়ার্ড কখনোই সরাসরি সেভ করা হয় না, শুধু hash করা ভার্সন
    hashed_password = Column(String, nullable=False)
    # প্রতিটা নতুন ইউজার শুরুতে কিছু ফ্রি credit পাবে (ভবিষ্যতে
    # পেমেন্ট/সাবস্ক্রিপশন ফিচারে কাজে লাগবে)
    credits = Column(Integer, default=10)
    plan = Column(String, default="free")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
