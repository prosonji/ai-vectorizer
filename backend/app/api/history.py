"""
History API (Step 9)

দুইটা endpoint:
    GET    /history  -> এখন পর্যন্ত ভেক্টরাইজ করা সব ছবির তালিকা
    DELETE /history   -> পুরো history তালিকা মুছে ফেলা (ফাইল মুছবে না, শুধু তালিকা)
"""

from fastapi import APIRouter

from app.database.history_store import get_all_history, clear_history

router = APIRouter()


@router.get("/history")
def list_history():
    """
    সব history entry ফেরত দেয়, সবচেয়ে নতুনটা সবার আগে।
    """
    entries = get_all_history()
    return {
        "status": "ok",
        "count": len(entries),
        "history": entries,
    }


@router.delete("/history")
def delete_history():
    """
    History তালিকা খালি করে দেয় (আসল ছবি/SVG ফাইল ডিস্কে থেকেই যায়)।
    """
    clear_history()
    return {
        "status": "ok",
        "message": "History তালিকা মুছে ফেলা হয়েছে",
    }
