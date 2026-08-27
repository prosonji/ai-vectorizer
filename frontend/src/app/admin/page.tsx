"use client";

/**
 * Admin Panel পেজ (Step 14)
 *
 * এই পেজে যা যা হবে:
 * 1. localStorage থেকে টোকেন নিয়ে backend এর /admin/stats, /admin/users,
 *    /admin/history কল করা
 * 2. ইউজার admin না হলে (403 error আসলে) "তোমার এই অ্যাক্সেস নাই" দেখানো
 * 3. admin হলে তিনটা সেকশন দেখানো: Stats, Users list, History list
 */

import { useEffect, useState } from "react";

const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL || "http://127.0.0.1:8000";

type Stats = {
  total_users: number;
  total_vectorized: number;
  color_mode_count: number;
  bw_mode_count: number;
};

type AdminUser = {
  id: number;
  name: string;
  email: string;
  credits: number;
  plan: string;
  is_admin: boolean;
  created_at: string | null;
};

type HistoryEntry = {
  image_id: string;
  mode: string;
  shapes_found: number;
  colors_used: number | null;
  created_at: string;
};

export default function AdminPage() {
  const [loading, setLoading] = useState(true);
  const [forbidden, setForbidden] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");

  const [stats, setStats] = useState<Stats | null>(null);
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [history, setHistory] = useState<HistoryEntry[]>([]);

  useEffect(() => {
    const token = localStorage.getItem("ai_vectorizer_token");

    if (!token) {
      setForbidden(true);
      setLoading(false);
      return;
    }

    const headers = { Authorization: `Bearer ${token}` };

    Promise.all([
      fetch(`${BACKEND_URL}/admin/stats`, { headers }),
      fetch(`${BACKEND_URL}/admin/users`, { headers }),
      fetch(`${BACKEND_URL}/admin/history`, { headers }),
    ])
      .then(async ([statsRes, usersRes, historyRes]) => {
        if (statsRes.status === 403 || usersRes.status === 403) {
          setForbidden(true);
          return;
        }
        setStats(await statsRes.json());
        setUsers(await usersRes.json());
        setHistory(await historyRes.json());
      })
      .catch(() => setErrorMessage("তথ্য লোড করা যায়নি"))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center text-gray-500">
        লোড হচ্ছে...
      </div>
    );
  }

  if (forbidden) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center gap-2">
        <p className="text-xl font-semibold text-gray-800">
          এই পেজ শুধু অ্যাডমিনদের জন্য
        </p>
        <p className="text-gray-500 text-sm">
          তোমার এই পেজ দেখার অনুমতি নাই।
        </p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 px-4 py-10">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-3xl font-bold text-gray-900 mb-8">Admin Panel</h1>

        {errorMessage && (
          <p className="text-red-600 text-sm mb-4">{errorMessage}</p>
        )}

        {stats && (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-10">
            <div className="bg-white rounded-xl border border-gray-200 p-4 text-center">
              <p className="text-2xl font-bold text-gray-900">{stats.total_users}</p>
              <p className="text-xs text-gray-500 mt-1">মোট ইউজার</p>
            </div>
            <div className="bg-white rounded-xl border border-gray-200 p-4 text-center">
              <p className="text-2xl font-bold text-gray-900">{stats.total_vectorized}</p>
              <p className="text-xs text-gray-500 mt-1">মোট ভেক্টরাইজ</p>
            </div>
            <div className="bg-white rounded-xl border border-gray-200 p-4 text-center">
              <p className="text-2xl font-bold text-gray-900">{stats.bw_mode_count}</p>
              <p className="text-xs text-gray-500 mt-1">কালো-সাদা</p>
            </div>
            <div className="bg-white rounded-xl border border-gray-200 p-4 text-center">
              <p className="text-2xl font-bold text-gray-900">{stats.color_mode_count}</p>
              <p className="text-xs text-gray-500 mt-1">রঙিন</p>
            </div>
          </div>
        )}

        <h2 className="text-lg font-semibold text-gray-800 mb-3">
          ইউজার তালিকা ({users.length})
        </h2>
        <div className="bg-white rounded-xl border border-gray-200 overflow-x-auto mb-10">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100 text-left text-gray-500">
                <th className="p-3">নাম</th>
                <th className="p-3">ইমেইল</th>
                <th className="p-3">Credit</th>
                <th className="p-3">Plan</th>
                <th className="p-3">Admin</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id} className="border-b border-gray-50">
                  <td className="p-3">{u.name}</td>
                  <td className="p-3 text-gray-500">{u.email}</td>
                  <td className="p-3">{u.credits}</td>
                  <td className="p-3">{u.plan}</td>
                  <td className="p-3">{u.is_admin ? "✅" : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <h2 className="text-lg font-semibold text-gray-800 mb-3">
          সাম্প্রতিক ভেক্টরাইজ ({history.length})
        </h2>
        <div className="bg-white rounded-xl border border-gray-200 overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100 text-left text-gray-500">
                <th className="p-3">Image ID</th>
                <th className="p-3">মোড</th>
                <th className="p-3">Shapes</th>
                <th className="p-3">সময়</th>
              </tr>
            </thead>
            <tbody>
              {history.slice(0, 50).map((h) => (
                <tr key={h.image_id} className="border-b border-gray-50">
                  <td className="p-3 font-mono text-xs">{h.image_id.slice(0, 8)}...</td>
                  <td className="p-3">{h.mode}</td>
                  <td className="p-3">{h.shapes_found}</td>
                  <td className="p-3 text-gray-500">{h.created_at}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
