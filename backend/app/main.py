"""
AI Vectorizer - Backend Entry Point
Step 1: শুধু একটা basic FastAPI server, যেটা চালু হয় কিনা টেস্ট করার জন্য।
Step 9: History ফিচার + uploads ফোল্ডার সরাসরি অ্যাক্সেসযোগ্য করা (থাম্বনেইলের জন্য)।
Step 10: Login/Register - ডাটাবেজ টেবিল তৈরি + auth endpoint যোগ করা।
Step 12: Security - Rate limiting (একজন ইউজার/IP খুব ঘনঘন request পাঠাতে না পারে)।
"""

import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.rate_limiter import limiter

from app.database.db import Base, engine
from app.models.user import User  # noqa: F401 - table তৈরির জন্য import করা জরুরি

from app.api.upload import router as upload_router
from app.api.vectorize import router as vectorize_router
from app.api.history import router as history_router
from app.api.auth import router as auth_router
from app.api.export import router as export_router

# Step 10: ডাটাবেজে এখনো টেবিল না থাকলে তৈরি করে দেওয়া (users টেবিল)।
# এটা সার্ভার চালু হওয়ার সময় একবার চলে - যদি টেবিল আগে থেকেই থাকে,
# কিছু বদলাবে না (নিরাপদ, বারবার চালালেও সমস্যা নাই)।
Base.metadata.create_all(bind=engine)

# FastAPI app তৈরি
app = FastAPI(
    title="AI Vectorizer API",
    description="PNG/JPG/WEBP -> SVG/EPS/PDF/DXF converter backend",
    version="0.12.0",
)

# ============================================================
# Step 12: Rate Limiting সেটাপ
# ============================================================
# slowapi লাইব্রেরি দিয়ে প্রতিটা IP address থেকে কতবার request
# আসছে সেটা ট্র্যাক করা হয়। কোনো IP অতিরিক্ত দ্রুত request পাঠালে
# (যেমন কেউ script দিয়ে বারবার আপলোড করার চেষ্টা করলে) তাকে সাময়িক
# সময়ের জন্য ব্লক করে "429 Too Many Requests" জবাব দেওয়া হয়।
# এটা সার্ভারকে অতিরিক্ত লোড/অপব্যবহার থেকে রক্ষা করে।
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS - পরে Next.js frontend থেকে এই backend কে কল করতে হবে,
# তাই এখনই সব origin থেকে request allow করে রাখছি (development এর জন্য)।
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Step 2: Upload router যোগ করা হলো - এখন /upload endpoint কাজ করবে
app.include_router(upload_router, tags=["Upload"])

# Step 3: Vectorize router যোগ করা হলো - এখন /vectorize আর /download endpoint কাজ করবে
app.include_router(vectorize_router, tags=["Vectorize"])

# Step 9: History router - এখন /history (GET/DELETE) endpoint কাজ করবে
app.include_router(history_router, tags=["History"])

# Step 10: Auth router - এখন /register, /login, /me endpoint কাজ করবে
app.include_router(auth_router, tags=["Auth"])

# Step 11: Export router - এখন /export/pdf/{id} আর /export/eps/{id} কাজ করবে
app.include_router(export_router, tags=["Export"])

# Step 9: uploads/ ফোল্ডারকে সরাসরি ব্রাউজার থেকে অ্যাক্সেসযোগ্য করা হলো
# (যেমন http://127.0.0.1:8000/uploads/xxxx.jpeg) - History তে আসল ছবির
# থাম্বনেইল দেখানোর জন্য এটা দরকার
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOADS_DIR = os.path.join(BACKEND_DIR, "..", "uploads")
os.makedirs(UPLOADS_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOADS_DIR), name="uploads")


@app.get("/")
def read_root():
    """
    Root endpoint - শুধু চেক করার জন্য যে server চালু আছে কিনা।
    """
    return {
        "status": "ok",
        "message": "AI Vectorizer backend is running",
    }


@app.get("/health")
def health_check():
    """
    Health check endpoint - deployment / monitoring এর জন্য দরকার হবে।
    """
    return {"status": "healthy"}
