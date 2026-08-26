"""
Database Connection (Step 10)

এতদিন History-এর জন্য আমরা শুধু একটা JSON ফাইল ব্যবহার করছিলাম।
কিন্তু Login/Register এর জন্য এখন একটা আসল "database" দরকার - কারণ
ইউজারের ইমেইল/পাসওয়ার্ড এর মতো তথ্য নিরাপদে, structured ভাবে রাখা লাগে,
আর একই সাথে অনেক ইউজার ম্যানেজ করতে হবে।

আমরা SQLite ব্যবহার করছি (PostgreSQL না) কারণ:
    - এটা একটা সাধারণ ফাইল (database/app.db) - আলাদা কোনো
      database সার্ভার ইনস্টল/চালু করা লাগে না, Windows-এ এক্সট্রা
      কোনো ঝামেলা নাই
    - ছোট/মাঝারি প্রজেক্টের জন্য এটাই যথেষ্ট
    - পরে সত্যিকারের অনেক ইউজার হলে PostgreSQL এ migrate করা সহজ,
      কারণ আমরা SQLAlchemy ব্যবহার করছি (শুধু DATABASE_URL বদলালেই হবে,
      বাকি কোড প্রায় একই থাকবে)
"""

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATABASE_DIR = os.path.join(BACKEND_DIR, "database")
os.makedirs(DATABASE_DIR, exist_ok=True)

DATABASE_URL = f"sqlite:///{os.path.join(DATABASE_DIR, 'app.db')}"

# SQLite এর জন্য এই connect_args দরকার - কারণ FastAPI প্রতিটা request
# আলাদা থ্রেডে হ্যান্ডেল করতে পারে, আর SQLite ডিফল্টভাবে এটা পছন্দ করে না
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# সব model (যেমন User) এই Base থেকে inherit করবে
Base = declarative_base()


def get_db():
    """
    FastAPI "dependency" - প্রতিটা API request-এ একটা নতুন database
    session দেয়, request শেষ হলে সেটা বন্ধ করে দেয়। এভাবে ব্যবহার
    করলে connection leak (session খোলা থেকে যাওয়া) হয় না।
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
