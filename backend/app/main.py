"""
AI Vectorizer - Backend Entry Point
Step 14: Admin Panel router + is_admin কলামের জন্য ছোট migration।

⚠️ গুরুত্বপূর্ণ নোট: SQLAlchemy এর Base.metadata.create_all() শুধু
"নতুন" টেবিল বানায় - যদি "users" টেবিল আগে থেকেই থাকে (যেমন তোমার
লাইভ Render ডিপ্লয়মেন্টে), সেটাতে নতুন কলাম (is_admin) স্বয়ংক্রিয়ভাবে
যোগ হয় না। তাই নিচে একটা ছোট, হাতে-লেখা migration যোগ করা হলো যেটা
চেক করে is_admin কলাম আছে কিনা, না থাকলে ALTER TABLE দিয়ে যোগ করে দেয়।
"""

import os
import sqlite3

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.rate_limiter import limiter

from app.database.db import Base, engine, DATABASE_DIR
from app.models.user import User  # noqa: F401

from app.api.upload import router as upload_router
from app.api.vectorize import router as vectorize_router
from app.api.history import router as history_router
from app.api.auth import router as auth_router
from app.api.export import router as export_router
from app.api.admin import router as admin_router


def run_sqlite_migrations():
    """
    Step 14: is_admin কলাম আগে থেকে থাকা "users" টেবিলে না থাকলে যোগ করা।
    এটা নিরাপদ - যদি কলাম আগে থেকেই থাকে, কিছু করবে না।
    """
    db_path = os.path.join(DATABASE_DIR, "app.db")
    if not os.path.exists(db_path):
        return  # এখনো ডাটাবেজ ফাইলই তৈরি হয়নি, নতুন করে বানানো হবে - migration লাগবে না

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("PRAGMA table_info(users)")
    columns = [row[1] for row in cursor.fetchall()]

    if columns and "is_admin" not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN is_admin BOOLEAN DEFAULT 0")
        conn.commit()

    conn.close()


# টেবিল তৈরি (নতুন হলে) + migration (পুরনো টেবিল থাকলে)
Base.metadata.create_all(bind=engine)
run_sqlite_migrations()

app = FastAPI(
    title="AI Vectorizer API",
    description="PNG/JPG/WEBP -> SVG/EPS/PDF/DXF converter backend",
    version="0.14.0",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UPLOAD_DIR = os.path.join(BACKEND_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")


@app.get("/")
def read_root():
    return {"status": "ok", "message": "AI Vectorizer backend is running"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}


app.include_router(upload_router, tags=["Upload"])
app.include_router(vectorize_router, tags=["Vectorize"])
app.include_router(history_router, tags=["History"])
app.include_router(auth_router, tags=["Auth"])
app.include_router(export_router, tags=["Export"])
app.include_router(admin_router, tags=["Admin"])
