"""
Admin API (Step 14)

চারটা endpoint:
    GET  /admin/stats            -> সংক্ষিপ্ত পরিসংখ্যান (মোট ইউজার, মোট vectorize)
    GET  /admin/users             -> সব ইউজারের তালিকা
    GET  /admin/history            -> সব vectorize history (সব ইউজারের একসাথে)
    POST /admin/promote            -> কাউকে admin বানানো (প্রথম admin বানানোর জন্য)

প্রথম Admin কীভাবে বানাবে (bootstrap সমস্যা):
    যখন কোনো ইউজারই এখনো admin না, তখন কাউকে admin বানাবে কীভাবে?
    এর জন্য একটা বিশেষ, গোপন "ADMIN_SETUP_KEY" ব্যবহার করছি - এটা
    environment variable এ সেট করা থাকবে (তুমি নিজে জানো, কেউ অনুমান
    করতে পারবে না)। /admin/promote এ এই key + একটা ইমেইল পাঠালে,
    সেই ইমেইলের ইউজারকে admin বানিয়ে দেওয়া হবে - টোকেন/লগইন ছাড়াই,
    কারণ প্রথমবার তো কোনো admin-ই নাই।

    ⚠️ প্রথম admin বানানোর পর, নিরাপত্তার জন্য environment variable
    থেকে ADMIN_SETUP_KEY মুছে ফেলা বা বদলে দেওয়া ভালো অভ্যাস।
"""

import os

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.database.db import get_db
from app.database.history_store import get_all_history
from app.models.user import User
from app.auth.security import get_current_admin_user

router = APIRouter()

ADMIN_SETUP_KEY = os.environ.get("ADMIN_SETUP_KEY", "")


class PromoteRequest(BaseModel):
    email: EmailStr
    setup_key: str


@router.post("/admin/promote")
def promote_to_admin(payload: PromoteRequest, db: Session = Depends(get_db)):
    """
    কাউকে admin বানানো - শুধু সঠিক ADMIN_SETUP_KEY দিলেই কাজ করবে।
    """
    if not ADMIN_SETUP_KEY or payload.setup_key != ADMIN_SETUP_KEY:
        raise HTTPException(status_code=403, detail="ভুল setup key")

    user = db.query(User).filter(User.email == payload.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="এই ইমেইলের কোনো ইউজার পাওয়া যায়নি")

    user.is_admin = True
    db.commit()

    return {"status": "ok", "message": f"{user.email} এখন admin"}


@router.get("/admin/stats")
def admin_stats(
    db: Session = Depends(get_db),
    _admin: User = Depends(get_current_admin_user),
):
    """মোট ইউজার, মোট vectorize অপারেশন, ইত্যাদি সংক্ষিপ্ত তথ্য"""
    total_users = db.query(User).count()
    history = get_all_history()

    total_vectorized = len(history)
    color_mode_count = sum(1 for h in history if h.get("mode") == "color")
    bw_mode_count = total_vectorized - color_mode_count

    return {
        "total_users": total_users,
        "total_vectorized": total_vectorized,
        "color_mode_count": color_mode_count,
        "bw_mode_count": bw_mode_count,
    }


@router.get("/admin/users")
def admin_list_users(
    db: Session = Depends(get_db),
    _admin: User = Depends(get_current_admin_user),
):
    """সব ইউজারের তালিকা (পাসওয়ার্ড ছাড়া)"""
    users = db.query(User).order_by(User.created_at.desc()).all()
    return [
        {
            "id": u.id,
            "name": u.name,
            "email": u.email,
            "credits": u.credits,
            "plan": u.plan,
            "is_admin": u.is_admin,
            "created_at": u.created_at.isoformat() if u.created_at else None,
        }
        for u in users
    ]


@router.get("/admin/history")
def admin_list_history(_admin: User = Depends(get_current_admin_user)):
    """সব ইউজারের সব vectorize history (সবচেয়ে নতুনটা আগে)"""
    return get_all_history()
