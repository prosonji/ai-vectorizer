# ============================================
# Frontend Dockerfile (Step 13)
#
# এটা "multi-stage build" - দুইটা ধাপে বানানো হচ্ছে:
#   ১. "builder" ধাপ - সব dependency ইনস্টল করে Next.js অ্যাপটা build করা
#   ২. চূড়ান্ত ধাপ - শুধু build হওয়া ফাইলগুলো নিয়ে ছোট, দ্রুত container
#      বানানো (builder ধাপের অতিরিক্ত dev-tools/ফাইল বাদ যায়)
# ============================================

FROM node:20-alpine AS builder

WORKDIR /app

# আগে শুধু package.json কপি করে ইনস্টল করা - এতে rebuild দ্রুত হয়
COPY package*.json ./
RUN npm install

COPY . .

# NEXT_PUBLIC_ দিয়ে শুরু হওয়া env variable গুলো build সময়েই দরকার হয়
# (Next.js এগুলো build এর মধ্যেই "bake" করে ফেলে)
ARG NEXT_PUBLIC_BACKEND_URL
ENV NEXT_PUBLIC_BACKEND_URL=$NEXT_PUBLIC_BACKEND_URL

RUN npm run build

# ---- চূড়ান্ত, হালকা ধাপ ----
FROM node:20-alpine

WORKDIR /app

COPY --from=builder /app/public ./public
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./package.json

EXPOSE 3000

CMD ["npm", "start"]
