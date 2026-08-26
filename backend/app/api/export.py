"""
Export API (Step 11)

তিনটা endpoint - আগে থেকে ভেক্টরাইজ করা SVG কে PDF/EPS হিসেবে, বা
মূল ছবি থেকে সরাসরি DXF হিসেবে ডাউনলোড করার জন্য:
    GET /export/pdf/{image_id}
    GET /export/eps/{image_id}
    GET /export/dxf/{image_id}

PDF/EPS একই প্যাটার্ন মেনে চলে:
    ১. আগে চেক করা - এই image_id এর SVG আসলেই আছে কিনা
       (মানে আগে /vectorize করা হয়েছে কিনা)
    ২. সেই ফরম্যাটে ফাইলটা আগে থেকেই বানানো আছে কিনা চেক করা
       (থাকলে আবার বানানোর দরকার নাই, সময় বাঁচবে - এটাকে বলে "caching")
    ৩. না থাকলে নতুন করে বানিয়ে outputs/ ফোল্ডারে সেভ করা
    ৪. ফাইলটা ডাউনলোডের জন্য পাঠিয়ে দেওয়া

DXF আলাদা - এটা SVG থেকে না গিয়ে সরাসরি মূল ছবি থেকে shape এর
কোণার পয়েন্ট বের করে বানানো হয় (কারণ DXF Bezier curve সহজে সাপোর্ট
করে না, আর এটা মূলত CNC/লেজার কাটিং এর জন্য - রঙ/ফিল না, শুধু
কাটার লাইন দরকার)।
"""

import os

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.exports.converters import svg_to_pdf, svg_to_eps
from app.exports.dxf_exporter import polygons_to_dxf
from app.ai.vectorizer import extract_polygons_for_dxf

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUTPUT_DIR = os.path.join(BACKEND_DIR, "outputs")
UPLOAD_DIR = os.path.join(BACKEND_DIR, "uploads")

router = APIRouter()


def _get_svg_path(image_id: str) -> str:
    """
    এই image_id এর SVG ফাইল outputs/ ফোল্ডারে আছে কিনা চেক করে,
    থাকলে তার path ফেরত দেয়, না থাকলে 404 error দেয়।
    """
    svg_path = os.path.join(OUTPUT_DIR, f"{image_id}.svg")
    if not os.path.exists(svg_path):
        raise HTTPException(
            status_code=404,
            detail="এই আইডির কোনো SVG পাওয়া যায়নি। আগে /vectorize করেছ তো?",
        )
    return svg_path


def _find_uploaded_image(image_id: str) -> str:
    """
    DXF এর জন্য মূল ছবির ফাইল দরকার (SVG না) - uploads/ ফোল্ডারে
    image_id.* প্যাটার্নে সেটা খুঁজে বের করা।
    """
    import glob

    matches = glob.glob(os.path.join(UPLOAD_DIR, f"{image_id}.*"))
    if not matches:
        raise HTTPException(
            status_code=404,
            detail=f"'{image_id}' আইডি দিয়ে কোনো আপলোড করা ছবি পাওয়া যায়নি।",
        )
    return matches[0]


@router.get("/export/pdf/{image_id}")
def export_pdf(image_id: str):
    """
    SVG কে PDF এ রূপান্তর করে ডাউনলোডের জন্য পাঠায়।
    """
    svg_path = _get_svg_path(image_id)
    pdf_path = os.path.join(OUTPUT_DIR, f"{image_id}.pdf")

    # আগে থেকে বানানো না থাকলে এখনই বানিয়ে নেওয়া
    if not os.path.exists(pdf_path):
        try:
            svg_to_pdf(svg_path, pdf_path)
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"PDF বানানোর সময় সমস্যা হয়েছে: {str(e)}",
            )

    return FileResponse(
        path=pdf_path,
        media_type="application/pdf",
        filename=f"{image_id}.pdf",
    )


@router.get("/export/eps/{image_id}")
def export_eps(image_id: str):
    """
    SVG কে EPS এ রূপান্তর করে ডাউনলোডের জন্য পাঠায়।
    """
    svg_path = _get_svg_path(image_id)
    eps_path = os.path.join(OUTPUT_DIR, f"{image_id}.eps")

    if not os.path.exists(eps_path):
        try:
            svg_to_eps(svg_path, eps_path)
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"EPS বানানোর সময় সমস্যা হয়েছে: {str(e)}",
            )

    return FileResponse(
        path=eps_path,
        media_type="application/postscript",
        filename=f"{image_id}.eps",
    )


@router.get("/export/dxf/{image_id}")
def export_dxf(image_id: str):
    """
    মূল ছবি থেকে সরাসরি shape এর কোণার পয়েন্ট বের করে DXF বানায়
    (CNC/CAD/লেজার-কাটিং সফটওয়্যারে ব্যবহারের জন্য)।
    """
    input_path = _find_uploaded_image(image_id)
    dxf_path = os.path.join(OUTPUT_DIR, f"{image_id}.dxf")

    if not os.path.exists(dxf_path):
        try:
            polygons, _width, _height = extract_polygons_for_dxf(input_path)
            polygons_to_dxf(polygons, dxf_path)
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"DXF বানানোর সময় সমস্যা হয়েছে: {str(e)}",
            )

    return FileResponse(
        path=dxf_path,
        media_type="application/dxf",
        filename=f"{image_id}.dxf",
    )
