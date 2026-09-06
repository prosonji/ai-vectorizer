"use client";

/**
 * Batch Vectorize পেজ (নতুন ফিচার)
 *
 * এই পেজে ইউজার একটা পুরো ফোল্ডার বাছাই করতে পারবে (তার ভিতরের সব
 * ছবি একসাথে দেখাবে), তারপর "সব ভেক্টরাইজ করো" চাপলে একটার পর একটা
 * (sequentially) প্রতিটা ছবি আপলোড + ভেক্টরাইজ হবে, আর প্রতিটার
 * রেজাল্ট (SVG ডাউনলোড লিংক সহ) নিচে দেখানো হবে।
 *
 * এটা backend-এর কোনো নতুন endpoint লাগে না - আগে থেকে থাকা
 * /upload আর /vectorize endpoint বারবার কল করেই কাজ চালানো হচ্ছে।
 */

import { useState } from "react";

const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL || "http://127.0.0.1:8000";

const ALLOWED_EXTENSIONS = [".png", ".jpg", ".jpeg", ".webp"];

type FileStatus = "waiting" | "processing" | "done" | "error";

type BatchItem = {
  file: File;
  status: FileStatus;
  svgUrl: string | null;
  shapesFound: number | null;
  errorMessage: string | null;
};

export default function BatchPage() {
  const [items, setItems] = useState<BatchItem[]>([]);
  const [isRunning, setIsRunning] = useState(false);

  /**
   * ফোল্ডার (বা একাধিক ফাইল) বাছাই হলে - শুধু বৈধ ইমেজ ফরম্যাট
   * (png/jpg/jpeg/webp) ফিল্টার করে তালিকায় যোগ করা হয়।
   */
  function handleFolderChange(event: React.ChangeEvent<HTMLInputElement>) {
    const files = event.target.files;
    if (!files) return;

    const imageFiles: File[] = [];
    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      const lowerName = file.name.toLowerCase();
      if (ALLOWED_EXTENSIONS.some((ext) => lowerName.endsWith(ext))) {
        imageFiles.push(file);
      }
    }

    setItems(
      imageFiles.map((file) => ({
        file,
        status: "waiting",
        svgUrl: null,
        shapesFound: null,
        errorMessage: null,
      }))
    );
  }

  /**
   * একটা একটা করে (sequentially, একসাথে না) প্রতিটা ফাইল প্রসেস করা।
   * সব একসাথে (parallel) পাঠালে backend এর free-tier সার্ভার ওভারলোড
   * হয়ে যেতে পারে, তাই ইচ্ছাকৃতভাবে একটার পর একটা করা হচ্ছে।
   */
  async function handleProcessAll() {
    setIsRunning(true);

    for (let i = 0; i < items.length; i++) {
      setItems((prev) =>
        prev.map((item, idx) =>
          idx === i ? { ...item, status: "processing" } : item
        )
      );

      try {
        const formData = new FormData();
        formData.append("file", items[i].file);

        const uploadRes = await fetch(`${BACKEND_URL}/upload`, {
          method: "POST",
          body: formData,
        });
        if (!uploadRes.ok) {
          const errData = await uploadRes.json();
          throw new Error(errData.detail || "আপলোড ব্যর্থ হয়েছে");
        }
        const uploadData = await uploadRes.json();

        const vectorizeRes = await fetch(
          `${BACKEND_URL}/vectorize/${uploadData.image_id}?mode=bw`,
          { method: "POST" }
        );
        if (!vectorizeRes.ok) {
          const errData = await vectorizeRes.json();
          throw new Error(errData.detail || "ভেক্টরাইজ করা যায়নি");
        }
        const vectorizeData = await vectorizeRes.json();

        setItems((prev) =>
          prev.map((item, idx) =>
            idx === i
              ? {
                  ...item,
                  status: "done",
                  svgUrl: `${BACKEND_URL}${vectorizeData.download_url}`,
                  shapesFound: vectorizeData.shapes_found,
                }
              : item
          )
        );
      } catch (error) {
        setItems((prev) =>
          prev.map((item, idx) =>
            idx === i
              ? {
                  ...item,
                  status: "error",
                  errorMessage:
                    error instanceof Error ? error.message : "সমস্যা হয়েছে",
                }
              : item
          )
        );
      }
    }

    setIsRunning(false);
  }

  const doneCount = items.filter((i) => i.status === "done").length;

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col items-center px-4 py-12">
      <div className="text-center mb-10">
        <h1 className="text-3xl font-bold text-gray-900">
          Batch Vectorize (ফোল্ডার একসাথে)
        </h1>
        <p className="text-gray-500 mt-2">
          একটা পুরো ফোল্ডার বাছাই করো, ভিতরের সব ছবি একসাথে ভেক্টরাইজ হবে
        </p>
        <a href="/" className="text-blue-600 text-sm hover:underline">
          ← একটা ছবির জন্য হোমপেজে ফিরে যাও
        </a>
      </div>

      {/* ---- ফোল্ডার বাছাই বক্স ---- */}
      <div className="w-full max-w-xl bg-white rounded-2xl shadow-sm border border-gray-200 p-8">
        <label className="block border-2 border-dashed border-blue-300 bg-blue-50/40 rounded-2xl p-8 text-center cursor-pointer hover:bg-blue-50 transition-colors">
          <input
            type="file"
            // webkitdirectory দিয়ে ব্রাউজার ফোল্ডার বাছাই করতে দেয়
            // (Chrome/Edge এ কাজ করে, Firefox এ সীমিত সাপোর্ট)
            // @ts-expect-error - webkitdirectory একটা non-standard attribute, TypeScript এর built-in টাইপে নাই
            webkitdirectory=""
            directory=""
            multiple
            onChange={handleFolderChange}
            className="hidden"
          />
          <p className="text-blue-600 font-bold italic">
            {items.length > 0
              ? `${items.length}টা ছবি পাওয়া গেছে`
              : "এখানে ক্লিক করে একটা ফোল্ডার বাছাই করো"}
          </p>
          <p className="text-gray-400 text-sm mt-1">
            ফোল্ডারের ভিতরের PNG/JPG/WEBP ছবিগুলো স্বয়ংক্রিয়ভাবে বাছাই হবে
          </p>
        </label>

        <button
          onClick={handleProcessAll}
          disabled={items.length === 0 || isRunning}
          className="w-full mt-4 bg-blue-600 text-white font-semibold py-3 rounded-full hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
        >
          {isRunning
            ? `প্রসেস হচ্ছে... (${doneCount}/${items.length})`
            : `সব ভেক্টরাইজ করো (${items.length}টা ছবি)`}
        </button>
      </div>

      {/* ---- রেজাল্ট গ্রিড ---- */}
      {items.length > 0 && (
        <div className="w-full max-w-4xl mt-10 grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4">
          {items.map((item, idx) => (
            <div
              key={idx}
              className="bg-white rounded-xl border border-gray-200 p-3"
            >
              <p className="text-xs text-gray-500 truncate mb-2">
                {item.file.name}
              </p>

              <div className="w-full h-24 bg-gray-50 rounded-lg flex items-center justify-center overflow-hidden">
                {item.status === "waiting" && (
                  <span className="text-gray-300 text-xs">অপেক্ষায়</span>
                )}
                {item.status === "processing" && (
                  <span className="text-blue-400 text-xs">প্রসেস হচ্ছে...</span>
                )}
                {item.status === "error" && (
                  <span className="text-red-400 text-xs px-2 text-center">
                    {item.errorMessage}
                  </span>
                )}
                {item.status === "done" && item.svgUrl && (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    src={item.svgUrl}
                    alt={item.file.name}
                    className="w-full h-full object-contain"
                  />
                )}
              </div>

              {item.status === "done" && item.svgUrl && (
                <a
                  href={item.svgUrl}
                  download
                  className="block text-center text-xs text-blue-600 hover:underline mt-2"
                >
                  SVG ডাউনলোড ↓
                </a>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
