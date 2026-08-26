"""
Vectorize API
Step 3: আপলোড হওয়া ছবিকে SVG-তে রূপান্তর করার endpoint।

Flow:
    1. ইউজার আগে /upload দিয়ে ছবি পাঠিয়েছে, একটা image_id পেয়েছে
    2. এখন /vectorize/{image_id} কল করবে
    3. আমরা uploads/ ফোল্ডারে সেই image_id এর ফাইল খুঁজে বের করি
    4. app/ai/vectorizer.py এর পাইপলাইন চালিয়ে SVG বানাই
    5. outputs/ ফোল্ডারে সেভ করি
    6. ইউজারকে জানাই SVG রেডি, এবং /download/{image_id} দিয়ে নামানো যাবে
"""

import os
import glob

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.ai.vectorizer import vectorize_image

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
def vectorize(image_id: str):
    """
    আপলোড হওয়া ছবিকে SVG তে রূপান্তর করে।
    """
    input_path = find_uploaded_file(image_id)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_svg_path = os.path.join(OUTPUT_DIR, f"{image_id}.svg")

    try:
        result = vectorize_image(input_path, output_svg_path)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"ভেক্টরাইজ করার সময় সমস্যা হয়েছে: {str(e)}",
        )

    return {
        "status": "ok",
        "message": "ছবি সফলভাবে ভেক্টরাইজ হয়েছে",
        "image_id": image_id,
        "width": result["width"],
        "height": result["height"],
        "shapes_found": result["shapes_found"],
        "download_url": f"/download/{image_id}",
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
