# AI Vectorizer — Step 1 (Project Setup)

এইটা পুরো প্রজেক্টের **প্রথম ধাপ**। এই ধাপে আমরা শুধু:
- ফোল্ডার স্ট্রাকচার বানিয়েছি
- একটা basic FastAPI backend বানিয়েছি (এখনো কোনো AI/vectorize ফিচার নাই)
- Python virtual environment (venv) সেটাপ করব

---

## ধাপ ১: Python ইনস্টল আছে কিনা চেক করো

টার্মিনাল / কমান্ড প্রম্পটে লিখো:

```bash
python --version
```

যদি `python` কাজ না করে, তাহলে `python3 --version` ট্রাই করো।
Python 3.10 বা তার উপরের ভার্সন থাকলে ভালো। না থাকলে https://www.python.org/downloads/ থেকে ইনস্টল করে নাও।

---

## ধাপ ২: প্রজেক্ট ফোল্ডারে যাও

```bash
cd ai-vectorizer/backend
```

---

## ধাপ ৩: Python ভার্চুয়াল এনভায়রনমেন্ট (venv) বানাও

তুমি বলেছিলে "python manager" দিয়ে বানাবে — এখানে আমরা Python এর বিল্ট-ইন **venv** ব্যবহার করছি (এটাই সবচেয়ে সহজ ও standard পদ্ধতি)।

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**Mac / Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

✅ Activate হলে টার্মিনালের শুরুতে `(venv)` লেখা দেখবে। এটা মানে তুমি এখন প্রজেক্টের নিজস্ব isolated python environment এর ভেতরে আছো — এখানে যা প্যাকেজ ইনস্টল করবে তা তোমার সিস্টেমের অন্য প্রজেক্টে প্রভাব ফেলবে না।

---

## ধাপ ৪: Requirements ইনস্টল করো

```bash
pip install -r requirements.txt
```

এটা `fastapi` আর `uvicorn` ইনস্টল করবে (server চালানোর জন্য দরকার)।

---

## ধাপ ৫: সার্ভার চালাও

```bash
uvicorn app.main:app --reload
```

টার্মিনালে এমন কিছু দেখবে:
```
Uvicorn running on http://127.0.0.1:8000
```

---

## ধাপ ৬: টেস্ট করো

ব্রাউজারে যাও: **http://127.0.0.1:8000**

দেখবে:
```json
{"status": "ok", "message": "AI Vectorizer backend is running"}
```

আরেকটা ভালো জিনিস — FastAPI স্বয়ংক্রিয়ভাবে API ডকুমেন্টেশন বানায়:
**http://127.0.0.1:8000/docs**

---

## ✅ এই ধাপ শেষ হলে

যদি উপরের সব ঠিকমতো কাজ করে (browser এ ok message দেখো), তাহলে কমেন্ট করো "step 1 হয়ে গেছে" — এরপর আমরা **Step 2: Image Upload API** বানাবো (ছবি আপলোড করার endpoint + file validation)।

---

## এখন পর্যন্ত ফোল্ডার স্ট্রাকচার

```
ai-vectorizer/
├── backend/
│   ├── app/
│   │   ├── main.py          ← FastAPI app (এইটা এখন কাজ করছে)
│   │   ├── __init__.py
│   │   ├── api/              ← পরে endpoint গুলো এখানে যাবে
│   │   ├── ai/                ← পরে vectorize AI logic এখানে যাবে
│   │   ├── models/
│   │   ├── database/
│   │   ├── auth/
│   │   ├── exports/
│   │   └── services/
│   ├── uploads/               ← ইউজারের আপলোড করা ছবি এখানে জমা হবে
│   ├── outputs/                ← ভেক্টর হওয়া ফাইল এখানে জমা হবে
│   └── requirements.txt
└── README.md (এই ফাইল)
```
