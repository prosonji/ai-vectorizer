"use client";

/**
 * AI Vectorizer - Homepage (পুনর্গঠিত, সব ফিচার সহ সম্পূর্ণ ভার্সন)
 *
 * এই পেজে যা যা আছে:
 * 1. Login/Register বক্স (উপরে ডানে)
 * 2. Upload + কালো-সাদা/রঙিন মোড টগল
 * 3. Before/After প্রিভিউ
 * 4. SVG/PDF/EPS/DXF ডাউনলোড
 * 5. History সেকশন (আগের সব কাজের তালিকা, থাম্বনেইল সহ)
 */

import { useEffect, useState } from "react";

const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL || "http://127.0.0.1:8000";

type Stage = "idle" | "uploading" | "uploaded" | "vectorizing" | "done" | "error";
type VectorizeMode = "bw" | "color";

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

type AuthUser = {
  id: number;
  name: string;
  email: string;
  credits: number;
  plan: string;
  is_admin?: boolean;
};

type AuthView = "none" | "login" | "register";

export default function Home() {
  // ---- Upload/Vectorize state ----
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [imageId, setImageId] = useState<string | null>(null);
  const [svgUrl, setSvgUrl] = useState<string | null>(null);
  const [stage, setStage] = useState<Stage>("idle");
  const [errorMessage, setErrorMessage] = useState<string>("");
  const [shapesFound, setShapesFound] = useState<number | null>(null);
  const [colorsUsed, setColorsUsed] = useState<number | null>(null);
  const [mode, setMode] = useState<VectorizeMode>("bw");

  // ---- History state ----
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const [historyLoading, setHistoryLoading] = useState<boolean>(true);

  // ---- Auth state ----
  const [authToken, setAuthToken] = useState<string | null>(null);
  const [authUser, setAuthUser] = useState<AuthUser | null>(null);
  const [authView, setAuthView] = useState<AuthView>("none");
  const [authName, setAuthName] = useState<string>("");
  const [authEmail, setAuthEmail] = useState<string>("");
  const [authPassword, setAuthPassword] = useState<string>("");
  const [authError, setAuthError] = useState<string>("");
  const [authSubmitting, setAuthSubmitting] = useState<boolean>(false);

  // ---- পেজ লোড হওয়ার সময়: history আনো, আর টোকেন থাকলে ইউজার আনো ----
  useEffect(() => {
    fetchHistory();

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

  function fetchHistory() {
    setHistoryLoading(true);
    fetch(`${BACKEND_URL}/history`)
      .then((res) => res.json())
      .then((data) => setHistory(Array.isArray(data) ? data : []))
      .catch(() => setHistory([]))
      .finally(() => setHistoryLoading(false));
  }

  async function handleClearHistory() {
    try {
      await fetch(`${BACKEND_URL}/history`, { method: "DELETE" });
      setHistory([]);
    } catch {
      // চুপচাপ ব্যর্থ হলেও সমস্যা নাই, ইউজারকে আটকাবে না
    }
  }

  function handleFileChange(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;

    setSelectedFile(file);
    setPreviewUrl(URL.createObjectURL(file));
    setImageId(null);
    setSvgUrl(null);
    setStage("idle");
    setErrorMessage("");
    setShapesFound(null);
    setColorsUsed(null);
  }

  async function handleUploadAndVectorize() {
    if (!selectedFile) return;

    try {
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

      setStage("vectorizing");

      const vectorizeResponse = await fetch(
        `${BACKEND_URL}/vectorize/${newImageId}?mode=${mode}`,
        { method: "POST" }
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

      fetchHistory();
    } catch (error) {
      setStage("error");
      setErrorMessage(
        error instanceof Error ? error.message : "একটা সমস্যা হয়েছে"
      );
    }
  }

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

  function handleLogout() {
    localStorage.removeItem("ai_vectorizer_token");
    setAuthToken(null);
    setAuthUser(null);
  }

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col items-center px-4 py-12">
      {/* ---- Auth বক্স (উপরে ডানে) ---- */}
      <div className="w-full max-w-xl flex justify-end mb-4">
        {authToken && authUser ? (
          <div className="flex items-center gap-3 text-sm">
            <span className="text-gray-600">
              স্বাগতম, <span className="font-medium">{authUser.name}</span>{" "}
              <span className="text-gray-400">({authUser.credits} credit)</span>
            </span>
            {authUser.is_admin && (
              <a href="/admin" className="text-purple-600 hover:underline">
                Admin
              </a>
            )}
            <button onClick={handleLogout} className="text-red-500 hover:underline">
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

                  {authError && <p className="text-xs text-red-600">{authError}</p>}

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
        {/* মোড বাছাই */}
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

        {stage === "error" && (
          <p className="mt-4 text-red-600 text-sm text-center">{errorMessage}</p>
        )}
      </div>

      {/* ---- Before / After প্রিভিউ ---- */}
      {previewUrl && (
        <div className="w-full max-w-3xl mt-10 grid grid-cols-1 sm:grid-cols-2 gap-6">
          <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-4">
            <p className="text-sm font-medium text-gray-500 mb-2">আসল ছবি</p>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={previewUrl}
              alt="Original"
              className="w-full h-64 object-contain rounded-lg bg-gray-100"
            />
          </div>

          <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-4">
            <p className="text-sm font-medium text-gray-500 mb-2">ভেক্টরাইজড (SVG)</p>
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
                  {stage === "vectorizing" ? "প্রসেস হচ্ছে..." : "এখনো ভেক্টরাইজ করা হয়নি"}
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

      {/* ---- History সেকশন ---- */}
      <div className="w-full max-w-3xl mt-16">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-bold text-gray-900">History</h2>
          {history.length > 0 && (
            <button
              onClick={handleClearHistory}
              className="text-xs text-red-500 hover:underline"
            >
              সব মুছে ফেলো
            </button>
          )}
        </div>

        {historyLoading && (
          <p className="text-gray-400 text-sm">History লোড হচ্ছে...</p>
        )}

        {!historyLoading && history.length === 0 && (
          <p className="text-gray-400 text-sm">
            এখনো কোনো ছবি ভেক্টরাইজ করা হয়নি। প্রথম ছবিটা আপলোড করে দেখো!
          </p>
        )}

        {!historyLoading && history.length > 0 && (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            {history.map((entry) => (
              <a
                key={entry.image_id}
                href={`${BACKEND_URL}${entry.svg_url}`}
                target="_blank"
                rel="noopener noreferrer"
                className="bg-white rounded-xl border border-gray-200 p-3 hover:shadow-md transition-shadow"
              >
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={`${BACKEND_URL}${entry.svg_url}`}
                  alt={entry.image_id}
                  className="w-full h-24 object-contain bg-gray-50 rounded-lg mb-2"
                />
                <p className="text-xs text-gray-400 truncate">
                  {entry.mode === "color" ? "রঙিন" : "কালো-সাদা"} ·{" "}
                  {entry.shapes_found} shape
                </p>
              </a>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
