"""
Upload API
Step 2: ইউজার এখান থেকে ছবি (PNG/JPG/JPEG/WEBP) আপলোড করবে।
Step 12: Security - Rate limiting + Pillow দিয়ে আসল ছবি কিনা যাচাই + dimension limit

এই ফাইলে যা যা আছে:
1. ফাইল টাইপ ভ্যালিডেশন (শুধু নির্দিষ্ট ইমেজ ফরম্যাট গ্রহণ করবে)
2. ফাইল সাইজ ভ্যালিডেশন (অনেক বড় ফাইল রিজেক্ট করবে)
3. Pillow দিয়ে ফাইলটা আসলেই একটা বৈধ, পড়া-যায়-এমন ছবি কিনা যাচাই করা
   (আগে শুধু extension/content-type হেডার চেক করা হতো, কিন্তু কেউ
   চাইলে একটা ক্ষতিকর ফাইলের নাম "photo.png" রেখে পাঠাতে পারত -
   হেডার চেক সেটা ধরতে পারে না। Pillow দিয়ে ফাইলটা সত্যিই খুলে
   দেখলে বোঝা যায় এটা আসল ছবি কিনা)
4. ছবির dimension (width/height) খুব বড় না কিনা চেক করা (অতিরিক্ত
   বড় ছবি সার্ভারের মেমোরি/CPU অনেক বেশি খরচ করতে পারে)
5. Rate limiting - একই IP থেকে মিনিটে বেশি হলে ১০ বার আপলোড করা যাবে
6. ফাইলটাকে ইউনিক নাম দিয়ে uploads/ ফোল্ডারে সেভ করা
7. একটা image_id ফেরত দেয়, যেটা পরের ধাপে (vectorize করার সময়) কাজে লাগবে
"""

import io
import os
import uuid

from fastapi import APIRouter, UploadFile, File, HTTPException, Request
from PIL import Image

from app.rate_limiter import limiter

# ============================================
# কনফিগারেশন (Settings)
# ============================================

# আমরা শুধু এই ফরম্যাটের ছবি গ্রহণ করব
ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}

# আমরা শুধু এই MIME টাইপ গ্রহণ করব (ব্রাউজার/client যা পাঠায় তার হেডার)
ALLOWED_CONTENT_TYPES = {"image/png", "image/jpeg", "image/webp"}

# সর্বোচ্চ ফাইল সাইজ: 10 MB (বাইটে হিসাব করা)
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

# সর্বোচ্চ ছবির width/height (পিক্সেলে) - এর চেয়ে বড় ছবি প্রসেস
# করতে গেলে সার্ভারের অনেক বেশি মেমোরি/সময় লাগতে পারে
MAX_DIMENSION = 6000

# uploads ফোল্ডারের path
# __file__ = এই ফাইলটার নিজের path (app/api/upload.py)
# তার থেকে তিন ধাপ উপরে গেলে backend/ ফোল্ডার পাওয়া যায়
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
UPLOAD_DIR = os.path.join(BACKEND_DIR, "uploads")

# একটা router বানাচ্ছি - এটাকে পরে main.py তে যোগ করা হবে
router = APIRouter()


@router.post("/upload")
@limiter.limit("10/minute")
async def upload_image(request: Request, file: UploadFile = File(...)):
    """
    ছবি আপলোড করার endpoint।

    কীভাবে কাজ করে:
    1. ফাইলের extension চেক করে (.png, .jpg, .jpeg, .webp কিনা)
    2. ফাইলের content-type চেক করে (আসলেই ইমেজ কিনা)
    3. ফাইলের সাইজ চেক করে (10MB এর বেশি না কিনা)
    4. Pillow দিয়ে খুলে যাচাই করে - ফাইলটা আসলেই একটা বৈধ ছবি কিনা
    5. ছবির dimension (width/height) খুব বড় না কিনা চেক করে
    6. সব ঠিক থাকলে uploads/ ফোল্ডারে একটা ইউনিক নাম দিয়ে সেভ করে
    7. একটা image_id ফেরত দেয়, যেটা পরের ধাপে (vectorize করার সময়) কাজে লাগবে

    ⚠️ @limiter.limit("10/minute") - একই IP থেকে মিনিটে ১০ বারের
    বেশি আপলোড করলে "429 Too Many Requests" error আসবে।
    """

    # ---- ধাপ ১: Extension চেক ----
    original_filename = file.filename or ""
    file_extension = os.path.splitext(original_filename)[1].lower()

    if file_extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=(
                f"'{file_extension}' ফরম্যাট সাপোর্ট করে না। "
                f"শুধু এগুলো দেওয়া যাবে: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
            ),
        )

    # ---- ধাপ ২: Content-Type চেক ----
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"'{file.content_type}' - এটা একটা বৈধ ইমেজ ফাইল মনে হচ্ছে না।",
        )

    # ---- ধাপ ৩: ফাইল পড়া ও সাইজ চেক ----
    file_bytes = await file.read()

    if len(file_bytes) == 0:
        raise HTTPException(status_code=400, detail="ফাইলটা খালি (0 বাইট)।")

    if len(file_bytes) > MAX_FILE_SIZE:
        size_mb = len(file_bytes) / (1024 * 1024)
        raise HTTPException(
            status_code=400,
            detail=f"ফাইলটা অনেক বড় ({size_mb:.1f}MB)। সর্বোচ্চ 10MB পর্যন্ত দেওয়া যাবে।",
        )

    # ---- ধাপ ৩.৫: Pillow দিয়ে যাচাই করা - এটা আসলেই একটা বৈধ ছবি কিনা ----
    # শুধু নাম/হেডার দেখে বোঝা যায় না ফাইলটা আসল ছবি কিনা - কেউ চাইলে
    # অন্য কিছুকে "photo.png" নাম দিয়ে পাঠাতে পারে। Pillow দিয়ে ফাইলটা
    # সত্যিকারভাবে খুলে দেখলে সেটা ধরা পড়ে।
    try:
        image_check = Image.open(io.BytesIO(file_bytes))
        image_check.verify()  # ছবির ডেটা ক্ষতিগ্রস্ত/জাল কিনা যাচাই করে
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="ফাইলটা আসলে একটা বৈধ ছবি বলে মনে হচ্ছে না (ক্ষতিগ্রস্ত বা ভুয়া ফাইল)।",
        )

    # verify() করার পর Image object আর ব্যবহার করা যায় না, তাই dimension
    # চেক করতে আবার নতুন করে খুলতে হচ্ছে
    image_for_size = Image.open(io.BytesIO(file_bytes))
    width, height = image_for_size.size

    if width > MAX_DIMENSION or height > MAX_DIMENSION:
        raise HTTPException(
            status_code=400,
            detail=(
                f"ছবির আকার অনেক বড় ({width}x{height} পিক্সেল)। "
                f"সর্বোচ্চ {MAX_DIMENSION}x{MAX_DIMENSION} পিক্সেল পর্যন্ত দেওয়া যাবে।"
            ),
        )

    # ---- ধাপ ৪: ইউনিক নাম বানিয়ে সেভ করা ----
    # uuid4() একটা র‍্যান্ডম, প্রায় সব সময় ইউনিক আইডি বানায়
    # যেমন: 3f2504e0-4f89-11d3-9a0c-0305e82c3301
    image_id = str(uuid.uuid4())
    saved_filename = f"{image_id}{file_extension}"
    saved_path = os.path.join(UPLOAD_DIR, saved_filename)

    # uploads ফোল্ডার না থাকলে বানিয়ে নাও (safety এর জন্য)
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    with open(saved_path, "wb") as f:
        f.write(file_bytes)

    # ---- ধাপ ৫: রেজাল্ট ফেরত দেওয়া ----
    return {
        "status": "ok",
        "message": "ছবি সফলভাবে আপলোড হয়েছে",
        "image_id": image_id,
        "original_filename": original_filename,
        "saved_filename": saved_filename,
        "size_kb": round(len(file_bytes) / 1024, 2),
    }
