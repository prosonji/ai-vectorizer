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

import { useEffect, useState } from "react";

const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL || "http://127.0.0.1:8000";

const ALLOWED_EXTENSIONS = [".png", ".jpg", ".jpeg", ".webp"];

// JSZip লাইব্রেরিটা npm দিয়ে ইনস্টল না করে, সরাসরি CDN (ইন্টারনেট)
// থেকে ব্রাউজারে লোড করা হবে - এতে package.json বদলানো বা আবার
// `npm install` করা লাগবে না।
declare global {
  interface Window {
    JSZip: any;
  }
}

type FileStatus = "waiting" | "processing" | "done" | "error";

type ExportFormat = "svg" | "pdf" | "eps" | "dxf";

const FORMAT_OPTIONS: { value: ExportFormat; label: string }[] = [
  { value: "svg", label: "SVG" },
  { value: "pdf", label: "PDF" },
  { value: "eps", label: "EPS" },
  { value: "dxf", label: "DXF" },
];

type OptimizeFor = "general" | "editing" | "cutting" | "custom";

const OPTIMIZE_OPTIONS: { value: OptimizeFor; label: string; hint: string }[] = [
  { value: "general", label: "সাধারণ ব্যবহার", hint: "ডিফল্ট, সব কাজে চলবে" },
  { value: "editing", label: "সহজ সম্পাদনা", hint: "কম পয়েন্ট, এডিট করা সহজ" },
  { value: "cutting", label: "কাটিং/এনগ্রেভিং", hint: "পরিষ্কার লাইন, লেজার-কাটের জন্য" },
  { value: "custom", label: "কাস্টম", hint: "নিজের মতো মোড বাছাই করো" },
];

type BatchItem = {
  file: File;
  status: FileStatus;
  imageId: string | null;
  svgUrl: string | null;
  shapesFound: number | null;
  errorMessage: string | null;
};

export default function BatchPage() {
  const [items, setItems] = useState<BatchItem[]>([]);
  const [isRunning, setIsRunning] = useState(false);
  const [isZipping, setIsZipping] = useState(false);
  const [format, setFormat] = useState<ExportFormat>("svg");
  const [optimizeFor, setOptimizeFor] = useState<OptimizeFor>("general");
  const [customMode, setCustomMode] = useState<"bw" | "color">("bw");

  // ---- পেজ লোড হওয়ার সময় CDN থেকে JSZip লোড করা ----
  useEffect(() => {
    if (window.JSZip) return; // আগে থেকে লোড থাকলে আবার লোড করার দরকার নাই

    const script = document.createElement("script");
    script.src =
      "https://cdnjs.cloudflare.com/ajax/libs/jszip/3.10.1/jszip.min.js";
    script.async = true;
    document.body.appendChild(script);
  }, []);

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
        imageId: null,
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

        const vectorizeMode = optimizeFor === "custom" ? customMode : "bw";
        const vectorizeRes = await fetch(
          `${BACKEND_URL}/vectorize/${uploadData.image_id}?mode=${vectorizeMode}&optimize_for=${optimizeFor}`,
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
                  imageId: uploadData.image_id,
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

  /**
   * নির্বাচিত format (svg/pdf/eps/dxf) অনুযায়ী একটা item এর
   * ডাউনলোড URL বানানো। SVG এর জন্য আগে থেকে vectorize করার সময়
   * পাওয়া svgUrl ব্যবহার হয়, বাকি ফরম্যাটের জন্য backend এর
   * /export/{format}/{image_id} endpoint কল করা হয়।
   */
  function getDownloadUrl(item: BatchItem, fmt: ExportFormat): string | null {
    if (fmt === "svg") return item.svgUrl;
    if (!item.imageId) return null;
    return `${BACKEND_URL}/export/${fmt}/${item.imageId}`;
  }

  /**
   * সফলভাবে vectorize হওয়া সব ছবি নির্বাচিত format এ একসাথে একটা
   * .zip ফাইলে বান্ডেল করে ডাউনলোড করা। SVG এর জন্য সরাসরি svgUrl
   * থেকে, আর PDF/EPS/DXF এর জন্য backend এর /export endpoint থেকে
   * প্রতিটা ফাইল আলাদা করে fetch করে JSZip এ যোগ করা হচ্ছে।
   */
  async function handleDownloadAllZip() {
    if (!window.JSZip) {
      alert("এক্ষুনি প্রস্তুত হচ্ছে, একটু পর আবার চেষ্টা করো");
      return;
    }

    setIsZipping(true);

    try {
      const zip = new window.JSZip();
      const doneItems = items.filter((i) => i.status === "done" && i.svgUrl);

      for (const item of doneItems) {
        const url = getDownloadUrl(item, format);
        if (!url) continue;

        const baseName = item.file.name.replace(/\.[^/.]+$/, "");

        if (format === "svg") {
          const response = await fetch(url);
          const svgText = await response.text();
          zip.file(`${baseName}.svg`, svgText);
        } else {
          const response = await fetch(url);
          if (!response.ok) continue;
          const blob = await response.blob();
          zip.file(`${baseName}.${format}`, blob);
        }
      }

      const zipBlob = await zip.generateAsync({ type: "blob" });
      const zipUrl = URL.createObjectURL(zipBlob);

      const link = document.createElement("a");
      link.href = zipUrl;
      link.download = `vectorized-images-${format}.zip`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(zipUrl);
    } catch {
      alert("ZIP বানাতে সমস্যা হয়েছে, আবার চেষ্টা করো");
    } finally {
      setIsZipping(false);
    }
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

        {/* ---- Optimize for (vectorizer.ai এর মতো প্রিসেট) ---- */}
        <div className="mt-4">
          <p className="text-xs text-gray-500 mb-2">Optimize for</p>
          <div className="grid grid-cols-2 gap-2">
            {OPTIMIZE_OPTIONS.map((opt) => (
              <button
                key={opt.value}
                type="button"
                onClick={() => setOptimizeFor(opt.value)}
                className={`text-left p-2 rounded-xl border text-xs transition-colors ${
                  optimizeFor === opt.value
                    ? "bg-blue-600 text-white border-blue-600"
                    : "bg-white text-gray-600 border-gray-300 hover:bg-gray-50"
                }`}
              >
                <div className="font-semibold">{opt.label}</div>
                <div
                  className={
                    optimizeFor === opt.value ? "text-blue-100" : "text-gray-400"
                  }
                >
                  {opt.hint}
                </div>
              </button>
            ))}
          </div>

          {/* ---- custom হলে mode (bw/color) বাছাই ---- */}
          {optimizeFor === "custom" && (
            <div className="mt-2 flex gap-2">
              <button
                type="button"
                onClick={() => setCustomMode("bw")}
                className={`flex-1 py-2 rounded-full text-xs font-semibold border transition-colors ${
                  customMode === "bw"
                    ? "bg-gray-900 text-white border-gray-900"
                    : "bg-white text-gray-600 border-gray-300"
                }`}
              >
                কালো-সাদা (BW)
              </button>
              <button
                type="button"
                onClick={() => setCustomMode("color")}
                className={`flex-1 py-2 rounded-full text-xs font-semibold border transition-colors ${
                  customMode === "color"
                    ? "bg-gray-900 text-white border-gray-900"
                    : "bg-white text-gray-600 border-gray-300"
                }`}
              >
                রঙিন (Color)
              </button>
            </div>
          )}
        </div>

        {/* ---- ফরম্যাট বাছাই (SVG/PDF/EPS/DXF) ---- */}
        <div className="mt-4">
          <p className="text-xs text-gray-500 mb-2">ডাউনলোড ফরম্যাট</p>
          <div className="grid grid-cols-4 gap-2">
            {FORMAT_OPTIONS.map((opt) => (
              <button
                key={opt.value}
                type="button"
                onClick={() => setFormat(opt.value)}
                className={`py-2 rounded-full text-sm font-semibold border transition-colors ${
                  format === opt.value
                    ? "bg-blue-600 text-white border-blue-600"
                    : "bg-white text-gray-600 border-gray-300 hover:bg-gray-50"
                }`}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>

        <button
          onClick={handleProcessAll}
          disabled={items.length === 0 || isRunning}
          className="w-full mt-4 bg-blue-600 text-white font-semibold py-3 rounded-full hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
        >
          {isRunning
            ? `প্রসেস হচ্ছে... (${doneCount}/${items.length})`
            : `সব ভেক্টরাইজ করো (${items.length}টা ছবি)`}
        </button>

        {/* ---- সব SVG একসাথে ZIP এ ডাউনলোড করার বাটন ----
            আগে এই বাটন শুধু doneCount > 0 হলে দেখানো হতো, এখন সবসময়
            দেখানো হয় (শুরুতে disabled থাকে), যাতে ইউজার প্রথম থেকেই
            বাটনটা দেখতে পায় এবং বুঝতে পারে এটা কী কাজ করবে। */}
        <button
          onClick={handleDownloadAllZip}
          disabled={isZipping || doneCount === 0}
          className="w-full mt-3 bg-gray-900 text-white font-semibold py-3 rounded-full hover:bg-gray-800 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
        >
          {isZipping
            ? "ZIP বানানো হচ্ছে..."
            : doneCount > 0
            ? `সব ${format.toUpperCase()} ডাউনলোড করো (ZIP) - ${doneCount}টা ফাইল`
            : `সব ${format.toUpperCase()} ডাউনলোড করো (ZIP)`}
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

              {item.status === "done" &&
                item.svgUrl &&
                (() => {
                  const url = getDownloadUrl(item, format);
                  if (!url) return null;
                  return (
                    <a
                      href={url}
                      download
                      className="block text-center text-xs text-blue-600 hover:underline mt-2"
                    >
                      {format.toUpperCase()} ডাউনলোড ↓
                    </a>
                  );
                })()}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
