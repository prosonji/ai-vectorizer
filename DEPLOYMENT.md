# AI Vectorizer — Deployment গাইড (Step 13)

এই গাইডে দুইটা অংশ আছে:
1. **লোকালি Docker দিয়ে টেস্ট করা** (তোমার কম্পিউটারেই, ইন্টারনেটে যাওয়ার আগে)
2. **ইন্টারনেটে ফ্রি হোস্টিং-এ লাইভ করা**

---

## অংশ ১: Docker Desktop ইনস্টল করা

Docker চালানোর জন্য একটা প্রোগ্রাম লাগবে — **Docker Desktop**।

1. যাও: https://www.docker.com/products/docker-desktop/
2. **"Download for Windows"** বাটনে ক্লিক করো
3. ডাউনলোড হওয়া `.exe` ফাইলে ডাবল-ক্লিক করে ইনস্টল করো (সব ডিফল্ট অপশন রেখে Next চাপতে থাকো)
4. ইনস্টল শেষে কম্পিউটার **রিস্টার্ট** করতে বলতে পারে — করে নাও
5. রিস্টার্টের পর Docker Desktop চালু করো (Start মেনু থেকে খুঁজে)
6. প্রথমবার চালু হতে একটু সময় নিবে, নিচে-ডানদিকে হোয়েল আইকন (🐳) দেখা গেলে বুঝবে চালু হয়েছে

### চেক করো Docker কাজ করছে কিনা

PowerShell খুলে লিখো:
```powershell
docker --version
```
ভার্সন নাম্বার দেখলে ঠিক আছে।

---

## অংশ ২: লোকালি Docker দিয়ে চালানো

প্রজেক্টের মূল ফোল্ডারে (`ai-vectorizer`, যার ভিতরে `backend` আর `frontend` দুইটাই আছে) গিয়ে:

```powershell
cd C:\Users\USER\Downloads\ai-vectorizer-step1\ai-vectorizer
docker compose up --build
```

এটা প্রথমবার একটু সময় নিবে (সব ইমেজ ডাউনলোড/বিল্ড হবে, ৫-১০ মিনিট)। শেষে backend আর frontend দুইটাই একসাথে চালু হয়ে যাবে।

ব্রাউজারে চেক করো:
- Frontend: http://localhost:3000
- Backend: http://localhost:8000/health

বন্ধ করতে চাইলে PowerShell-এ **Ctrl + C**, তারপর:
```powershell
docker compose down
```

---

## অংশ ৩: ইন্টারনেটে ফ্রি হোস্টিং-এ লাইভ করা

এখানে **GitHub** লাগবে (তোমার কোড অনলাইনে রাখার জায়গা) এবং একটা হোস্টিং সার্ভিস। **Render.com** একটা ভালো ফ্রি-টিয়ার অপশন (ক্রেডিট কার্ড ছাড়াই শুরু করা যায়)।

### ধাপ ১: GitHub-এ কোড আপলোড করো

1. https://github.com এ একটা ফ্রি অ্যাকাউন্ট বানাও (না থাকলে)
2. একটা নতুন repository বানাও (নাম: `ai-vectorizer`)
3. তোমার প্রজেক্ট ফোল্ডার GitHub-এ পুশ করো (এর জন্য Git ইনস্টল থাকা লাগবে — চাইলে এই ধাপে আমি আলাদাভাবে সাহায্য করতে পারি)

### ধাপ ২: Render-এ Backend ডিপ্লয় করো

1. https://render.com এ অ্যাকাউন্ট বানাও, GitHub দিয়ে সাইন-ইন করো
2. **"New +"** → **"Web Service"**
3. তোমার `ai-vectorizer` repository বেছে নাও
4. **Root Directory:** `backend`
5. **Runtime:** Docker (Render নিজেই `Dockerfile` খুঁজে পাবে)
6. Environment Variables-এ যোগ করো: `JWT_SECRET_KEY` = (একটা লম্বা, র‍্যান্ডম টেক্সট)
7. **Deploy** চাপো — কিছুক্ষণ পর একটা পাবলিক URL পাবে (যেমন `https://ai-vectorizer-backend.onrender.com`)

### ধাপ ৩: Render-এ Frontend ডিপ্লয় করো

1. আবার **"New +"** → **"Web Service"**
2. একই repository, কিন্তু **Root Directory:** `frontend`
3. Environment Variables-এ যোগ করো: `NEXT_PUBLIC_BACKEND_URL` = (ধাপ ২ থেকে পাওয়া backend URL)
4. **Deploy** চাপো

⚠️ **নোট:** Render, Railway এর মতো সার্ভিসের ফ্রি-টিয়ারের শর্ত (কতক্ষণ চালু থাকে, সীমা কী) মাঝেমধ্যে বদলায় — deploy করার সময় তাদের বর্তমান pricing পেজ একবার দেখে নিও।

---

## ✅ এই ধাপ শেষে যা থাকলো

- Docker সেটাপ (`Dockerfile` দুইটা + `docker-compose.yml`) — লোকালি এক কমান্ডে সব চালানো যায়
- Frontend এখন hardcoded backend URL এর বদলে environment variable ব্যবহার করে (deploy করার সময় সহজে বদলানো যায়)
- ইন্টারনেটে লাইভ করার একটা বাস্তবসম্মত রোডম্যাপ

GitHub-এ কোড তোলা বা Render-এ deploy করার সময় কোথাও আটকালে জানিও — একসাথে ধাপে ধাপে করব।
