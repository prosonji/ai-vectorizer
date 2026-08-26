"""
Vectorize API
Step 3: আপলোড হওয়া ছবিকে SVG-তে রূপান্তর করার endpoint।
Step 7: এখন mode প্যারামিটার দিয়ে "bw" (কালো-সাদা) বা "color" (রঙিন) - দুইভাবেই ভেক্টরাইজ করা যায়।

Flow:
    1. ইউজার আগে /upload দিয়ে ছবি পাঠিয়েছে, একটা image_id পেয়েছে
    2. এখন /vectorize/{image_id}?mode=bw অথবা ?mode=color দিয়ে কল করবে
    3. আমরা uploads/ ফোল্ডারে সেই image_id এর ফাইল খুঁজে বের করি
    4. app/ai/vectorizer.py এর পাইপলাইন চালিয়ে SVG বানাই (mode অনুযায়ী)
    5. outputs/ ফোল্ডারে সেভ করি
    6. ইউজারকে জানাই SVG রেডি, এবং /download/{image_id} দিয়ে নামানো যাবে
"""

import os
import glob
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query, Depends, Request
from fastapi.responses import FileResponse
from typing import Literal
from sqlalchemy.orm import Session

from app.ai.vectorizer import vectorize_image
from app.database.history_store import add_history_entry
from app.database.db import get_db
from app.models.user import User
from app.auth.security import get_current_user_optional
from app.rate_limiter import limiter

# ============================================
# ফোল্ডার path গুলো ঠিক করা
# ============================================
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
UPLOAD_DIR = os.path.join(BACKEND_DIR, "uploads")
OUTPUT_DIR = os.path.join(BACKEND_DIR, "outputs")

router = APIRouter()


def find_uploaded_file(image_id: str) -> str:
    """
    image_id দিয়ে uploads/ ফোল্ডারে ফাইলটা খুঁজে বের করা।
    আমরা extension জানি না (হতে পারে .png, .jpg, .jpeg, .webp),
    তাই glob দিয়ে "image_id.*" প্যাটার্নে খুঁজছি।
    """
    matches = glob.glob(os.path.join(UPLOAD_DIR, f"{image_id}.*"))
    if not matches:
        raise HTTPException(
            status_code=404,
            detail=f"'{image_id}' আইডি দিয়ে কোনো আপলোড করা ছবি পাওয়া যায়নি। আগে /upload করেছ তো?",
        )
    return matches[0]


@router.post("/vectorize/{image_id}")
@limiter.limit("20/minute")
def vectorize(
    request: Request,
    image_id: str,
    mode: Literal["bw", "color"] = Query(
        default="bw",
        description="'bw' = কালো-সাদা মোড, 'color' = রঙিন মোড",
    ),
    num_colors: int = Query(
        default=8,
        ge=2,
        le=32,
        description="Color মোডে কতগুলো মূল রঙে ভাগ করা হবে (২-৩২)",
    ),
    current_user: User | None = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    """
    আপলোড হওয়া ছবিকে SVG তে রূপান্তর করে।
    mode='bw' দিলে কালো-সাদা, mode='color' দিলে রঙিন ভেক্টরাইজ হবে।

    Step 12 - Credit সিস্টেম:
        - লগইন করা ইউজার হলে - তার credit ০ বা তার কম হলে আটকে দেওয়া হয়,
          সফল হলে ১টা credit কমিয়ে দেওয়া হয়
        - লগইন না করা (guest) ইউজার - কোনো বাধা ছাড়াই আগের মতো ব্যবহার
          করতে পারবে (নতুন ইউজারদের টুলটা আগে try করার সুযোগ দেওয়ার জন্য)
    """
    # ---- Step 12: Credit চেক (শুধু লগইন করা ইউজারের জন্য) ----
    if current_user is not None and current_user.credits <= 0:
        raise HTTPException(
            status_code=402,
            detail="তোমার credit শেষ হয়ে গেছে। আরও credit লাগবে।",
        )

    input_path = find_uploaded_file(image_id)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_svg_path = os.path.join(OUTPUT_DIR, f"{image_id}.svg")

    try:
        result = vectorize_image(input_path, output_svg_path, mode=mode, num_colors=num_colors)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"ভেক্টরাইজ করার সময় সমস্যা হয়েছে: {str(e)}",
        )

    # ---- Step 12: সফল হলে লগইন করা ইউজারের ১টা credit কমানো ----
    remaining_credits = None
    if current_user is not None:
        current_user.credits -= 1
        db.commit()
        db.refresh(current_user)
        remaining_credits = current_user.credits

    # ---- Step 9: History তে একটা রেকর্ড যোগ করা ----
    # original_filename: uploads/ ফোল্ডারে সেভ করা ফাইলের নাম (extension সহ),
    # এটা দিয়েই আমরা /uploads/... URL বানিয়ে থাম্বনেইল দেখাতে পারব
    original_saved_filename = os.path.basename(input_path)

    history_entry = {
        "image_id": image_id,
        "mode": result.get("mode", mode),
        "shapes_found": result["shapes_found"],
        "colors_used": result.get("colors_used"),
        "width": result["width"],
        "height": result["height"],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "original_url": f"/uploads/{original_saved_filename}",
        "svg_url": f"/download/{image_id}",
    }
    add_history_entry(history_entry)

    return {
        "status": "ok",
        "message": "ছবি সফলভাবে ভেক্টরাইজ হয়েছে",
        "image_id": image_id,
        "mode": result.get("mode", mode),
        "width": result["width"],
        "height": result["height"],
        "shapes_found": result["shapes_found"],
        "colors_used": result.get("colors_used"),
        "download_url": f"/download/{image_id}",
        "remaining_credits": remaining_credits,
    }


@router.get("/download/{image_id}")
def download_svg(image_id: str):
    """
    ভেক্টরাইজ হওয়া SVG ফাইলটা ডাউনলোড করার endpoint।
    """
    svg_path = os.path.join(OUTPUT_DIR, f"{image_id}.svg")

    if not os.path.exists(svg_path):
        raise HTTPException(
            status_code=404,
            detail="এই আইডির কোনো SVG পাওয়া যায়নি। আগে /vectorize করেছ তো?",
        )

    return FileResponse(
        path=svg_path,
        media_type="image/svg+xml",
        filename=f"{image_id}.svg",
    )
