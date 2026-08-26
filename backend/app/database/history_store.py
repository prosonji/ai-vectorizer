"""
History Store (Step 9)

এখানে আমরা এখনো আসল SQL database (PostgreSQL/SQLite) ব্যবহার করছি না -
আপাতত একটা সহজ JSON ফাইলেই সব vectorize-এর ইতিহাস (history) জমা রাখছি।

কেন এভাবে শুরু করা হলো:
    - এত ছোট স্কেলে (একজন/অল্প কয়েকজন ইউজার) JSON ফাইলই যথেষ্ট
    - Database (Step ১০/১১ এর দিকে যখন Login/Register আসবে) তখন
      পুরো জিনিসটা সহজেই SQLAlchemy/PostgreSQL এ migrate করা যাবে,
      কারণ এই ফাইলের বাইরের ফাংশনগুলো (get_all_history, add_history_entry)
      একই রকম থাকবে - শুধু ভিতরের implementation পাল্টাবে
"""

import json
import os
import threading

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATABASE_DIR = os.path.join(BACKEND_DIR, "database")
HISTORY_FILE = os.path.join(DATABASE_DIR, "history.json")

# একসাথে একাধিক request থেকে ফাইলে লেখার সময় যাতে কনফ্লিক্ট না হয়,
# তার জন্য একটা lock ব্যবহার করছি
_lock = threading.Lock()


def _ensure_file_exists() -> None:
    """
    history.json ফাইল না থাকলে খালি লিস্ট দিয়ে একটা নতুন ফাইল বানানো।
    """
    os.makedirs(DATABASE_DIR, exist_ok=True)
    if not os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump([], f)


def get_all_history() -> list:
    """
    এখন পর্যন্ত জমা হওয়া সব history entry ফেরত দেয়,
    সবচেয়ে নতুনটা সবার আগে (most recent first)।
    """
    _ensure_file_exists()
    with _lock:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            entries = json.load(f)
    # সবচেয়ে নতুন এন্ট্রি আগে দেখানোর জন্য লিস্টটা উল্টে দিচ্ছি
    return list(reversed(entries))


def add_history_entry(entry: dict) -> None:
    """
    একটা নতুন history entry (dict আকারে) ফাইলের শেষে যোগ করা।
    """
    _ensure_file_exists()
    with _lock:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            entries = json.load(f)

        entries.append(entry)

        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(entries, f, indent=2, ensure_ascii=False)


def clear_history() -> None:
    """
    সব history entry মুছে ফেলা (DELETE /history endpoint এর জন্য)।
    এটা শুধু history.json ফাইলের রেকর্ড মুছে দেয়, আসল ছবি/SVG ফাইল
    uploads/outputs ফোল্ডারে থেকেই যায় (সেগুলো মুছতে চাইলে আলাদা লজিক লাগবে)।
    """
    _ensure_file_exists()
    with _lock:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump([], f)
