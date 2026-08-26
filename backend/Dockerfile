# ============================================
# Backend Dockerfile (Step 13)
#
# এটা একটা "রেসিপি" - Docker কে বলে দেয় কীভাবে আমাদের backend
# চালানোর জন্য একটা container বানাতে হবে, ধাপে ধাপে।
# ============================================

# ভিত্তি হিসেবে একটা হালকা, Python 3.12 ইনস্টল করা Linux ইমেজ ব্যবহার করছি
# (Python 3.14 এখনো নতুন, official Docker ইমেজে স্থিতিশীলভাবে পাওয়া যায়
# 3.12 - আর আমাদের কোডে এমন কিছু নাই যা শুধু 3.14-তেই চলবে)
FROM python:3.12-slim

# OpenCV এর জন্য কিছু সিস্টেম-লেভেল লাইব্রেরি দরকার (Linux এ এগুলো
# আলাদা করে ইনস্টল করা লাগে, Windows এ pip নিজেই সব বান্ডিল করে দেয়)
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Container এর ভিতরে কাজ করার ফোল্ডার ঠিক করা
WORKDIR /app

# আগে শুধু requirements.txt কপি করে ইনস্টল করছি (পুরো কোড না) -
# এটা একটা common trick: কোড বদলালেও, requirements.txt না বদলালে
# Docker আগের ইনস্টল করা প্যাকেজগুলো পুনরায় ব্যবহার করবে (rebuild দ্রুত হবে)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# এবার বাকি সব কোড কপি করা
COPY . .

# Container এর কোন পোর্ট বাইরে খোলা থাকবে তা জানিয়ে দেওয়া
EXPOSE 8000

# Container চালু হলে এই কমান্ডটা চলবে (আমাদের uvicorn সার্ভার)
# --host 0.0.0.0 জরুরি - এটা ছাড়া container এর বাইরে থেকে সার্ভারে
# পৌঁছানো যাবে না
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
