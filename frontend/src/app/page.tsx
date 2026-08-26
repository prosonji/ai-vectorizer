"use client";

/**
 * Step 4: Homepage - Upload + Vectorize UI
 * Step 7: এখন "কালো-সাদা" আর "রঙিন" - দুইটা মোড বাছাই করা যাবে
 *
 * এই পেজে যা যা হবে:
 * 1. ইউজার একটা ছবি বাছাই করবে (file input দিয়ে)
 * 2. ইউজার মোড বাছাই করবে - কালো-সাদা নাকি রঙিন
 * 3. "Upload" বাটনে চাপলে backend এর /upload এ ছবি পাঠানো হবে
 * 4. সফল হলে backend এর /vectorize/{id}?mode=... কল হবে
 * 5. রেজাল্ট হিসেবে original ছবি আর SVG - দুইটা পাশাপাশি (before/after) দেখানো হবে
 * 6. একটা Download বাটন থাকবে SVG নামানোর জন্য
 *
 * "use client" - এই লাইনটা উপরে দেওয়া মানে এই component ব্রাউজারে চলবে
 * (কারণ আমরা এখানে useState, onClick এর মতো interactive জিনিস ব্যবহার করছি,
 * যেগুলো শুধু সার্ভারে চলা কোডে করা যায় না)
 */

import { useState, useEffect } from "react";

// আমাদের backend সার্ভারের ঠিকানা
// Step 13: এখন এটা environment variable থেকে আসে - লোকাল কম্পিউটারে
// চালানোর সময় এটা খালি থাকলে ডিফল্ট 127.0.0.1:8000 ব্যবহার হয়,
// কিন্তু ইন্টারনেটে লাইভ করার সময় NEXT_PUBLIC_BACKEND_URL সেট করে
// দিলে সেই আসল/পাবলিক backend ঠিকানা ব্যবহার হবে
const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL || "http://127.0.0.1:8000";

// আপলোডের ধাপগুলো ট্র্যাক করার জন্য একটা "state" - এটা বলবে এখন কোন অবস্থায় আছি
type Stage = "idle" | "uploading" | "uploaded" | "vectorizing" | "done" | "error";

// Step 7: ভেক্টরাইজ করার মোড - কালো-সাদা নাকি রঙিন
type VectorizeMode = "bw" | "color";

// Step 9: History তে প্রতিটা entry এর গঠন (backend যা পাঠায় তার সাথে মিলিয়ে)
type HistoryEntry = {
  image_id: string;
  mode: VectorizeMode;
  shapes_found: number;
  colors_used: number | null;
  width: number;
  height: number;
  created_at: string;
  original_url: string;
  svg_url: string;
};

// Step 10: লগইন করা ইউজারের তথ্য
type AuthUser = {
  id: number;
  name: string;
  email: string;
  credits: number;
  plan: string;
};

// Step 10: এখন অথ বক্সে কী দেখানো হচ্ছে - কিছুই না, লগইন ফর্ম, নাকি রেজিস্টার ফর্ম
type AuthView = "none" | "login" | "register";

export default function Home() {
  // ---- State গুলো ----
  // selectedFile: ইউজার যে ফাইলটা বেছেছে
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  // previewUrl: বাছাই করা ছবিটা প্রিভিউ দেখানোর জন্য একটা সাময়িক লিংক
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  // imageId: backend থেকে পাওয়া ইউনিক আইডি
  const [imageId, setImageId] = useState<string | null>(null);
  // svgUrl: ভেক্টরাইজ হওয়ার পর SVG ডাউনলোড/দেখার লিংক
  const [svgUrl, setSvgUrl] = useState<string | null>(null);
  // stage: এখন কী হচ্ছে (idle/uploading/uploaded/vectorizing/done/error)
  const [stage, setStage] = useState<Stage>("idle");
  // errorMessage: কোনো সমস্যা হলে সেই বার্তা
  const [errorMessage, setErrorMessage] = useState<string>("");
  // shapesFound: কয়টা shape/আকৃতি পাওয়া গেছে (তথ্য হিসেবে দেখানোর জন্য)
  const [shapesFound, setShapesFound] = useState<number | null>(null);
  // colorsUsed: color মোডে কয়টা রঙ ব্যবহার হয়েছে
  const [colorsUsed, setColorsUsed] = useState<number | null>(null);
  // mode: ইউজার এখন কোন মোড বেছেছে - ডিফল্ট "bw" (কালো-সাদা)
  const [mode, setMode] = useState<VectorizeMode>("bw");
  // Step 9: history - আগের সব ভেক্টরাইজ করা ছবির তালিকা
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const [historyLoading, setHistoryLoading] = useState<boolean>(true);

  // ---- Step 10: Login/Register এর জন্য state ----
  const [authToken, setAuthToken] = useState<string | null>(null);
  const [authUser, setAuthUser] = useState<AuthUser | null>(null);
  const [authView, setAuthView] = useState<AuthView>("none");
  const [authName, setAuthName] = useState<string>("");
  const [authEmail, setAuthEmail] = useState<string>("");
  const [authPassword, setAuthPassword] = useState<string>("");
  const [authError, setAuthError] = useState<string>("");
  const [authSubmitting, setAuthSubmitting] = useState<boolean>(false);

  /**
   * Step 10: পেজ প্রথমবার লোড হওয়ার সময়, ব্রাউজারের localStorage এ
   * আগের কোনো লগইন টোকেন সেভ করা আছে কিনা চেক করা। থাকলে সেটা দিয়ে
   * /me কল করে ইউজারের তথ্য আনা হয় - এভাবে পেজ রিফ্রেশ করলেও ইউজার
   * লগইন অবস্থায়ই থাকে (বারবার লগইন করা লাগে না)।
   */
  useEffect(() => {
    const savedToken = localStorage.getItem("ai_vectorizer_token");
    if (!savedToken) return;

    fetch(`${BACKEND_URL}/me`, {
      headers: { Authorization: `Bearer ${savedToken}` },
    })
      .then((res) => {
        if (!res.ok) throw new Error("session expired");
        return res.json();
      })
      .then((user) => {
        setAuthToken(savedToken);
        setAuthUser(user);
      })
      .catch(() => {
        localStorage.removeItem("ai_vectorizer_token");
      });
  }, []);

  /**
   * Step 10: রেজিস্টার বা লগইন ফর্ম সাবমিট করলে এই ফাংশন কল হয়।
   * isRegister দিয়ে বোঝা যায় কোন endpoint কল করতে হবে।
   */
  async function handleAuthSubmit(isRegister: boolean) {
    setAuthError("");
    setAuthSubmitting(true);

    try {
      const endpoint = isRegister ? "/register" : "/login";
      const body = isRegister
        ? { name: authName, email: authEmail, password: authPassword }
        : { email: authEmail, password: authPassword };

      const response = await fetch(`${BACKEND_URL}${endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "একটা সমস্যা হয়েছে");
      }

      // সফল হলে টোকেন সেভ করা - localStorage এ রাখলে পেজ রিফ্রেশ
      // করলেও লগইন অবস্থা মনে থাকবে
      localStorage.setItem("ai_vectorizer_token", data.access_token);
      setAuthToken(data.access_token);
      setAuthUser(data.user);
      setAuthView("none");
      setAuthName("");
      setAuthEmail("");
      setAuthPassword("");
    } catch (error) {
      setAuthError(error instanceof Error ? error.message : "একটা সমস্যা হয়েছে");
    } finally {
      setAuthSubmitting(false);
    }
  }

  /**
   * Step 10: লগআউট করলে টোকেন মুছে ফেলা - localStorage থেকেও, state থেকেও
   */
  function handleLogout() {
    localStorage.removeItem("ai_vectorizer_token");
    setAuthToken(null);
    setAuthUser(null);
  }

  /**
   * Step 9: backend থেকে history তালিকা নিয়ে আসা।
   * পেজ প্রথমবার লোড হওয়ার সময়, আর প্রতিবার নতুন vectorize সফল হওয়ার
   * পরেও এটা আবার কল হবে - যাতে তালিকা সবসময় সবচেয়ে নতুন থাকে।
   */
  async function fetchHistory() {
    try {
      setHistoryLoading(true);
      const response = await fetch(`${BACKEND_URL}/history`);
      if (!response.ok) return;
      const data = await response.json();
      setHistory(data.history || []);
    } catch {
      // history লোড করতে ব্যর্থ হলেও মূল অ্যাপ কাজ করতে থাকুক -
      // তাই এখানে কোনো error দেখানো হচ্ছে না, চুপচাপ ব্যর্থ হতে দিচ্ছি
    } finally {
      setHistoryLoading(false);
    }
  }

  // পেজ প্রথমবার লোড হওয়ার সময় একবার history আনা হবে
  useEffect(() => {
    fetchHistory();
  }, []);

  /**
   * Step 9: "History মুছে ফেলো" বাটনে ক্লিক করলে - backend এর
   * DELETE /history কল করে তালিকা খালি করে দেওয়া হয়। (আসল ছবি/SVG
   * ফাইল ডিস্কে থেকেই যায়, শুধু তালিকাটা খালি হয়)
   */
  async function handleClearHistory() {
    try {
      await fetch(`${BACKEND_URL}/history`, { method: "DELETE" });
      setHistory([]);
    } catch {
      // ব্যর্থ হলেও চুপচাপ থাকুক, মূল অ্যাপ কাজ করতে থাকবে
    }
  }

  /**
   * একটা ISO timestamp কে সহজে পড়া যায় এমন ফরম্যাটে দেখানো
   */
  function formatTimestamp(isoString: string): string {
    const date = new Date(isoString);
    return date.toLocaleString("bn-BD", {
      day: "numeric",
      month: "short",
      hour: "2-digit",
      minute: "2-digit",
    });
  }

  /**
   * ইউজার যখন ফাইল বাছাই করে (file input থেকে)
   */
  function handleFileChange(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;

    setSelectedFile(file);
    setPreviewUrl(URL.createObjectURL(file)); // ব্রাউজারেই সাময়িক প্রিভিউ লিংক বানানো
    setImageId(null);
    setSvgUrl(null);
    setStage("idle");
    setErrorMessage("");
    setShapesFound(null);
    setColorsUsed(null);
  }

  /**
   * "Upload & Vectorize" বাটনে ক্লিক করলে - দুইটা কাজ একসাথে করব:
   * প্রথমে upload, তারপর সাথে সাথে vectorize
   */
  async function handleUploadAndVectorize() {
    if (!selectedFile) return;

    try {
      // ---- ধাপ ১: Upload ----
      setStage("uploading");
      setErrorMessage("");

      const formData = new FormData();
      formData.append("file", selectedFile);

      const uploadResponse = await fetch(`${BACKEND_URL}/upload`, {
        method: "POST",
        body: formData,
      });

      if (!uploadResponse.ok) {
        const errData = await uploadResponse.json();
        throw new Error(errData.detail || "আপলোড ব্যর্থ হয়েছে");
      }

      const uploadData = await uploadResponse.json();
      const newImageId = uploadData.image_id;
      setImageId(newImageId);
      setStage("uploaded");

      // ---- ধাপ ২: Vectorize (upload সফল হওয়ার পর সাথে সাথেই) ----
      setStage("vectorizing");

      // Step 12: লগইন করা থাকলে Authorization header পাঠানো - এতে
      // backend বুঝতে পারবে কার credit কমাতে হবে (guest হলে header
      // পাঠানো হয় না, backend তখন credit-check ছাড়াই কাজ করে)
      const vectorizeHeaders: Record<string, string> = {};
      if (authToken) {
        vectorizeHeaders["Authorization"] = `Bearer ${authToken}`;
      }

      const vectorizeResponse = await fetch(
        `${BACKEND_URL}/vectorize/${newImageId}?mode=${mode}`,
        { method: "POST", headers: vectorizeHeaders }
      );

      if (!vectorizeResponse.ok) {
        const errData = await vectorizeResponse.json();
        throw new Error(errData.detail || "ভেক্টরাইজ করা যায়নি");
      }

      const vectorizeData = await vectorizeResponse.json();
      setShapesFound(vectorizeData.shapes_found);
      setColorsUsed(vectorizeData.colors_used ?? null);
      setSvgUrl(`${BACKEND_URL}${vectorizeData.download_url}`);
      setStage("done");

      // Step 12: backend থেকে remaining_credits পাওয়া গেলে (মানে
      // লগইন করা ছিল), লোকাল ইউজার state ও আপডেট করে দেওয়া - এতে
      // উপরের "স্বাগতম" বক্সে credit সংখ্যা সাথে সাথে বদলে যাবে
      if (vectorizeData.remaining_credits !== null && vectorizeData.remaining_credits !== undefined) {
        setAuthUser((prev) =>
          prev ? { ...prev, credits: vectorizeData.remaining_credits } : prev
        );
      }

      // এই ভেক্টরাইজটাও history তে যোগ হয়ে গেছে (backend এ), তাই
      // তালিকাটা আবার লোড করে নিচ্ছি যাতে নতুনটাও দেখা যায়
      fetchHistory();
    } catch (error) {
      setStage("error");
      setErrorMessage(
        error instanceof Error ? error.message : "একটা সমস্যা হয়েছে"
      );
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col items-center px-4 py-12">
      {/* ---- Step 10: Auth বক্স (উপরে ডানদিকে) ---- */}
      <div className="w-full max-w-xl flex justify-end mb-4">
        {authToken && authUser ? (
          <div className="flex items-center gap-3 text-sm">
            <span className="text-gray-600">
              স্বাগতম, <span className="font-medium">{authUser.name}</span>{" "}
              <span className="text-gray-400">({authUser.credits} credit)</span>
            </span>
            <button
              onClick={handleLogout}
              className="text-red-500 hover:underline"
            >
              লগআউট
            </button>
          </div>
        ) : (
          <div className="flex flex-col items-end gap-2">
            {authView === "none" && (
              <div className="flex gap-3 text-sm">
                <button
                  onClick={() => {
                    setAuthView("login");
                    setAuthError("");
                  }}
                  className="text-gray-700 hover:underline"
                >
                  লগইন
                </button>
                <button
                  onClick={() => {
                    setAuthView("register");
                    setAuthError("");
                  }}
                  className="text-blue-600 font-medium hover:underline"
                >
                  রেজিস্টার
                </button>
              </div>
            )}

            {(authView === "login" || authView === "register") && (
              <div className="w-72 bg-white rounded-xl shadow-sm border border-gray-200 p-4">
                <div className="flex items-center justify-between mb-3">
                  <p className="text-sm font-medium text-gray-800">
                    {authView === "login" ? "লগইন করো" : "নতুন অ্যাকাউন্ট বানাও"}
                  </p>
                  <button
                    onClick={() => setAuthView("none")}
                    className="text-gray-400 hover:text-gray-600 text-sm"
                  >
                    ✕
                  </button>
                </div>

                <div className="flex flex-col gap-2">
                  {authView === "register" && (
                    <input
                      type="text"
                      placeholder="নাম"
                      value={authName}
                      onChange={(e) => setAuthName(e.target.value)}
                      className="border border-gray-200 rounded-lg px-3 py-2 text-sm"
                    />
                  )}
                  <input
                    type="email"
                    placeholder="ইমেইল"
                    value={authEmail}
                    onChange={(e) => setAuthEmail(e.target.value)}
                    className="border border-gray-200 rounded-lg px-3 py-2 text-sm"
                  />
                  <input
                    type="password"
                    placeholder="পাসওয়ার্ড"
                    value={authPassword}
                    onChange={(e) => setAuthPassword(e.target.value)}
                    className="border border-gray-200 rounded-lg px-3 py-2 text-sm"
                  />

                  {authError && (
                    <p className="text-xs text-red-600">{authError}</p>
                  )}

                  <button
                    onClick={() => handleAuthSubmit(authView === "register")}
                    disabled={authSubmitting}
                    className="bg-gray-900 text-white text-sm font-medium py-2 rounded-lg hover:bg-gray-800 disabled:bg-gray-300 mt-1"
                  >
                    {authSubmitting
                      ? "একটু অপেক্ষা করো..."
                      : authView === "register"
                      ? "রেজিস্টার করো"
                      : "লগইন করো"}
                  </button>

                  <button
                    onClick={() =>
                      setAuthView(authView === "register" ? "login" : "register")
                    }
                    className="text-xs text-gray-400 hover:text-gray-600 mt-1"
                  >
                    {authView === "register"
                      ? "আগে থেকেই অ্যাকাউন্ট আছে? লগইন করো"
                      : "অ্যাকাউন্ট নাই? রেজিস্টার করো"}
                  </button>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* ---- হেডার ---- */}
      <div className="text-center mb-10">
        <h1 className="text-4xl font-bold text-gray-900">AI Vectorizer</h1>
        <p className="text-gray-500 mt-2">
          PNG / JPG / WEBP ছবি থেকে SVG ভেক্টর বানাও
        </p>
      </div>

      {/* ---- আপলোড বক্স ---- */}
      <div className="w-full max-w-xl bg-white rounded-2xl shadow-sm border border-gray-200 p-8">
        {/* ---- Step 7: মোড বাছাই - কালো-সাদা নাকি রঙিন ---- */}
        <div className="flex gap-2 mb-4">
          <button
            type="button"
            onClick={() => setMode("bw")}
            className={`flex-1 py-2 rounded-lg text-sm font-medium transition-colors ${
              mode === "bw"
                ? "bg-gray-900 text-white"
                : "bg-gray-100 text-gray-600 hover:bg-gray-200"
            }`}
          >
            কালো-সাদা
          </button>
          <button
            type="button"
            onClick={() => setMode("color")}
            className={`flex-1 py-2 rounded-lg text-sm font-medium transition-colors ${
              mode === "color"
                ? "bg-gray-900 text-white"
                : "bg-gray-100 text-gray-600 hover:bg-gray-200"
            }`}
          >
            রঙিন
          </button>
        </div>

        <label className="block border-2 border-dashed border-gray-300 rounded-xl p-8 text-center cursor-pointer hover:border-blue-400 transition-colors">
          <input
            type="file"
            accept=".png,.jpg,.jpeg,.webp"
            onChange={handleFileChange}
            className="hidden"
          />
          <span className="text-gray-600">
            {selectedFile
              ? selectedFile.name
              : "এখানে ক্লিক করে একটা ছবি বাছাই করো"}
          </span>
        </label>

        <button
          onClick={handleUploadAndVectorize}
          disabled={!selectedFile || stage === "uploading" || stage === "vectorizing"}
          className="w-full mt-4 bg-blue-600 text-white font-semibold py-3 rounded-xl hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
        >
          {stage === "uploading" && "আপলোড হচ্ছে..."}
          {stage === "vectorizing" && "ভেক্টরাইজ হচ্ছে..."}
          {(stage === "idle" || stage === "uploaded" || stage === "done" || stage === "error") &&
            "Upload & Vectorize"}
        </button>

        {/* ---- এরর মেসেজ ---- */}
        {stage === "error" && (
          <p className="mt-4 text-red-600 text-sm text-center">
            {errorMessage}
          </p>
        )}
      </div>

      {/* ---- Before / After প্রিভিউ ---- */}
      {previewUrl && (
        <div className="w-full max-w-3xl mt-10 grid grid-cols-1 sm:grid-cols-2 gap-6">
          {/* Original */}
          <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-4">
            <p className="text-sm font-medium text-gray-500 mb-2">আসল ছবি</p>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={previewUrl}
              alt="Original"
              className="w-full h-64 object-contain rounded-lg bg-gray-100"
            />
          </div>

          {/* Vectorized */}
          <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-4">
            <p className="text-sm font-medium text-gray-500 mb-2">
              ভেক্টরাইজড (SVG)
            </p>
            <div className="w-full h-64 rounded-lg bg-gray-100 flex items-center justify-center">
              {svgUrl ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={svgUrl}
                  alt="Vectorized SVG"
                  className="w-full h-64 object-contain"
                />
              ) : (
                <span className="text-gray-400 text-sm">
                  {stage === "vectorizing"
                    ? "প্রসেস হচ্ছে..."
                    : "এখনো ভেক্টরাইজ করা হয়নি"}
                </span>
              )}
            </div>

            {svgUrl && (
              <div className="mt-3 flex items-center justify-between">
                <span className="text-xs text-gray-400">
                  {shapesFound !== null && `${shapesFound}টা shape`}
                  {colorsUsed !== null && ` · ${colorsUsed}টা রঙ`}
                  {(shapesFound !== null || colorsUsed !== null) && " পাওয়া গেছে"}
                </span>
                <a
                  href={svgUrl}
                  download
                  className="text-blue-600 text-sm font-medium hover:underline"
                >
                  SVG ডাউনলোড করো ↓
                </a>
              </div>
            )}

            {/* ---- Step 11: অন্য ফরম্যাটে এক্সপোর্ট (PDF/EPS/DXF) ---- */}
            {svgUrl && imageId && (
              <div className="mt-2 flex gap-2">
                <a
                  href={`${BACKEND_URL}/export/pdf/${imageId}`}
                  download
                  className="flex-1 text-center text-xs bg-gray-100 text-gray-700 py-1.5 rounded-lg hover:bg-gray-200 transition-colors"
                >
                  PDF
                </a>
                <a
                  href={`${BACKEND_URL}/export/eps/${imageId}`}
                  download
                  className="flex-1 text-center text-xs bg-gray-100 text-gray-700 py-1.5 rounded-lg hover:bg-gray-200 transition-colors"
                >
                  EPS
                </a>
                <a
                  href={`${BACKEND_URL}/export/dxf/${imageId}`}
                  download
                  className="flex-1 text-center text-xs bg-gray-100 text-gray-700 py-1.5 rounded-lg hover:bg-gray-200 transition-colors"
                >
                  DXF
                </a>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ---- Step 9: History সেকশন ---- */}
      <div className="w-full max-w-4xl mt-16">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold text-gray-900">History</h2>
          {history.length > 0 && (
            <button
              onClick={handleClearHistory}
              className="text-xs text-gray-400 hover:text-red-500 transition-colors"
            >
              সব মুছে ফেলো
            </button>
          )}
        </div>

        {historyLoading && (
          <p className="text-sm text-gray-400">লোড হচ্ছে...</p>
        )}

        {!historyLoading && history.length === 0 && (
          <p className="text-sm text-gray-400">
            এখনো কোনো ছবি ভেক্টরাইজ করা হয়নি। প্রথম ছবিটা আপলোড করে দেখো!
          </p>
        )}

        {!historyLoading && history.length > 0 && (
          <div className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-6 gap-4">
            {history.map((entry) => (
              <div
                key={entry.image_id}
                className="bg-white rounded-xl border border-gray-200 p-2 hover:shadow-md transition-shadow"
              >
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={`${BACKEND_URL}${entry.svg_url}`}
                  alt="History thumbnail"
                  className="w-full h-20 object-contain rounded-lg bg-gray-50"
                />
                <div className="mt-2 flex items-center justify-between">
                  <span
                    className={`text-[10px] px-1.5 py-0.5 rounded-full ${
                      entry.mode === "color"
                        ? "bg-purple-100 text-purple-600"
                        : "bg-gray-100 text-gray-600"
                    }`}
                  >
                    {entry.mode === "color" ? "রঙিন" : "কালো-সাদা"}
                  </span>
                  <span className="text-[10px] text-gray-400">
                    {formatTimestamp(entry.created_at)}
                  </span>
                </div>
                <a
                  href={`${BACKEND_URL}${entry.svg_url}`}
                  download
                  className="block text-center text-[10px] text-blue-600 hover:underline mt-1"
                >
                  ডাউনলোড
                </a>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
