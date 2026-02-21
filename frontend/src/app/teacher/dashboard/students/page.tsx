"use client";

import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "@/lib/auth-context";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type StudentRow = {
  student_id: string;
  name: string;
  email?: string;
  risk_score: number;
  risk_band: "LOW" | "MEDIUM" | "HIGH";
  reasons: string[];
  active_counts: {
    competency: number;
    partial_understanding: number;
    misconception: number;
  };
  last_activity?: string | null;
};

type StudentsResponse = {
  page: number;
  limit: number;
  total: number;
  items: StudentRow[];
};

function riskStyle(risk: string) {
  if (risk === "HIGH") return { bg: "#ffe7e7", fg: "#ef4444" };
  if (risk === "MEDIUM") return { bg: "#fff6cc", fg: "#ca8a04" };
  return { bg: "#dcfce7", fg: "#16a34a" };
}

export default function TeacherStudentsPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { getIdToken } = useAuth();
  const [risk, setRisk] = useState<"" | "HIGH" | "MEDIUM" | "LOW">(
    (searchParams.get("risk") as "" | "HIGH" | "MEDIUM" | "LOW") || ""
  );
  const [grade, setGrade] = useState<"" | `${number}`>(searchParams.get("grade") as "" | `${number}` || "");
  const [textbookGrade, setTextbookGrade] = useState<"" | `${number}`>(searchParams.get("textbook_grade") as "" | `${number}` || "");
  const [subject, setSubject] = useState(searchParams.get("subject") || "");
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [data, setData] = useState<StudentsResponse | null>(null);

  useEffect(() => {
    setRisk((searchParams.get("risk") as "" | "HIGH" | "MEDIUM" | "LOW") || "");
    setGrade((searchParams.get("grade") as "" | `${number}`) || "");
    setTextbookGrade((searchParams.get("textbook_grade") as "" | `${number}`) || "");
    setSubject(searchParams.get("subject") || "");
    setPage(1);
  }, [searchParams]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError("");
      try {
        const token = await getIdToken();
        if (!token) {
          router.push("/auth");
          return;
        }
        const q = new URLSearchParams();
        q.set("page", String(page));
        q.set("limit", "25");
        if (risk) q.set("risk", risk);
        if (grade) q.set("grade", grade);
        if (textbookGrade) q.set("textbook_grade", textbookGrade);
        if (subject) q.set("subject", subject);
        const res = await fetch(`${API_URL}/api/teachers/me/dashboard/students?${q.toString()}`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        const j = await res.json();
        if (!res.ok) throw new Error(j?.detail || "Failed to load students");
        if (!cancelled) setData(j);
      } catch (e: unknown) {
        if (!cancelled) setError(e instanceof Error ? e.message : "Failed");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [getIdToken, page, risk, grade, textbookGrade, subject, router]);

  return (
    <main style={{ background: "#f5f8f8", minHeight: "calc(100vh - 72px)", padding: "1.2rem 1.6rem 2rem" }}>
      <div style={{ maxWidth: 1200, margin: "0 auto", display: "flex", flexDirection: "column", gap: "1rem" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "end", gap: "0.8rem" }}>
          <div>
            <h1 style={{ margin: 0 }}>Student Roster</h1>
            <div style={{ color: "#64748b", fontWeight: 600, marginTop: 4 }}>Institute-scoped risk monitoring</div>
          </div>
          <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
            <select
              value={grade}
              onChange={(e) => {
                const q = new URLSearchParams(searchParams.toString());
                if (e.target.value) q.set("grade", e.target.value);
                else q.delete("grade");
                q.delete("page");
                router.replace(`/teacher/dashboard/students?${q.toString()}`);
              }}
              style={{ padding: "0.5rem 0.8rem", borderRadius: 10, border: "1px solid #e2e8f0", background: "#fff", fontWeight: 700 }}
            >
              <option value="">All Grades</option>
              {Array.from({ length: 12 }, (_, i) => i + 1).map((g) => (
                <option key={g} value={String(g)}>
                  Grade {g}
                </option>
              ))}
            </select>
            <select
              value={textbookGrade}
              onChange={(e) => {
                const q = new URLSearchParams(searchParams.toString());
                if (e.target.value) q.set("textbook_grade", e.target.value);
                else q.delete("textbook_grade");
                q.delete("subject");
                q.delete("page");
                router.replace(`/teacher/dashboard/students?${q.toString()}`);
              }}
              style={{ padding: "0.5rem 0.8rem", borderRadius: 10, border: "1px solid #e2e8f0", background: "#fff", fontWeight: 700 }}
            >
              <option value="">All Textbook Grades</option>
              {Array.from({ length: 12 }, (_, i) => i + 1).map((g) => (
                <option key={g} value={String(g)}>
                  Textbook Grade {g}
                </option>
              ))}
            </select>
            <input
              value={subject}
              onChange={(e) => {
                const q = new URLSearchParams(searchParams.toString());
                if (e.target.value.trim()) q.set("subject", e.target.value.trim());
                else q.delete("subject");
                q.delete("page");
                router.replace(`/teacher/dashboard/students?${q.toString()}`);
              }}
              placeholder="Subject (e.g. Physics)"
              style={{ padding: "0.5rem 0.8rem", borderRadius: 10, border: "1px solid #e2e8f0", background: "#fff", fontWeight: 700, minWidth: 180 }}
            />
            <select
              value={risk}
              onChange={(e) => {
                const q = new URLSearchParams(searchParams.toString());
                if (e.target.value) q.set("risk", e.target.value);
                else q.delete("risk");
                q.delete("page");
                router.replace(`/teacher/dashboard/students?${q.toString()}`);
              }}
              style={{ padding: "0.5rem 0.8rem", borderRadius: 10, border: "1px solid #e2e8f0", background: "#fff", fontWeight: 700 }}
            >
              <option value="">All Risk Levels</option>
              <option value="HIGH">High Risk</option>
              <option value="MEDIUM">Medium Risk</option>
              <option value="LOW">Low Risk</option>
            </select>
          </div>
        </div>

        {error && <div style={{ color: "#be123c", background: "#fff1f2", border: "1px solid #fecdd3", borderRadius: 10, padding: "0.7rem 0.9rem", fontWeight: 700 }}>{error}</div>}

        <div style={{ background: "#fff", border: "1px solid #e2e8f0", borderRadius: 12, overflow: "hidden" }}>
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead style={{ background: "#f8fafc", color: "#64748b", textTransform: "uppercase", fontSize: "0.72rem", letterSpacing: "0.08em", fontWeight: 800 }}>
              <tr>
                <th style={{ padding: "0.7rem 0.9rem", textAlign: "left" }}>Name</th>
                <th style={{ padding: "0.7rem 0.9rem", textAlign: "left" }}>Risk</th>
                <th style={{ padding: "0.7rem 0.9rem", textAlign: "left" }}>Score</th>
                <th style={{ padding: "0.7rem 0.9rem", textAlign: "left" }}>Active Insights</th>
                <th style={{ padding: "0.7rem 0.9rem", textAlign: "right" }}>Action</th>
              </tr>
            </thead>
            <tbody>
              {(data?.items || []).map((s) => {
                const rs = riskStyle(s.risk_band);
                return (
                  <tr key={s.student_id} style={{ borderTop: "1px solid #f1f5f9" }}>
                    <td style={{ padding: "0.8rem 0.9rem" }}>
                      <div style={{ fontWeight: 700 }}>{s.name}</div>
                      <div style={{ color: "#94a3b8", fontSize: "0.82rem" }}>{s.student_id}</div>
                    </td>
                    <td style={{ padding: "0.8rem 0.9rem" }}>
                      <span style={{ background: rs.bg, color: rs.fg, padding: "0.2rem 0.55rem", borderRadius: 999, fontSize: "0.7rem", fontWeight: 800, textTransform: "uppercase", letterSpacing: "0.08em" }}>
                        {s.risk_band}
                      </span>
                    </td>
                    <td style={{ padding: "0.8rem 0.9rem", fontWeight: 700 }}>{s.risk_score}</td>
                    <td style={{ padding: "0.8rem 0.9rem", color: "#334155" }}>
                      C {s.active_counts.competency} / P {s.active_counts.partial_understanding} / M {s.active_counts.misconception}
                    </td>
                    <td style={{ padding: "0.8rem 0.9rem", textAlign: "right" }}>
                      <button
                        onClick={() => router.push(`/teacher/dashboard/students/${encodeURIComponent(s.student_id)}`)}
                        style={{ border: "1px solid #cbd5e1", borderRadius: 8, background: "#fff", padding: "0.35rem 0.55rem", fontWeight: 700, cursor: "pointer" }}
                      >
                        Open
                      </button>
                    </td>
                  </tr>
                );
              })}
              {!loading && (data?.items || []).length === 0 && (
                <tr>
                  <td colSpan={5} style={{ textAlign: "center", padding: "1rem", color: "#64748b", fontWeight: 600 }}>
                    No students in this filter.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div style={{ color: "#64748b", fontWeight: 600 }}>Page {data?.page || page}</div>
          <div style={{ display: "flex", gap: "0.5rem" }}>
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page <= 1}
              style={{ border: "1px solid #cbd5e1", borderRadius: 8, padding: "0.42rem 0.65rem", background: "#fff", cursor: page <= 1 ? "not-allowed" : "pointer", opacity: page <= 1 ? 0.5 : 1 }}
            >
              Prev
            </button>
            <button
              onClick={() => setPage((p) => p + 1)}
              disabled={!!data && data.items.length < 25}
              style={{ border: "1px solid #cbd5e1", borderRadius: 8, padding: "0.42rem 0.65rem", background: "#fff", cursor: data && data.items.length < 25 ? "not-allowed" : "pointer", opacity: data && data.items.length < 25 ? 0.5 : 1 }}
            >
              Next
            </button>
          </div>
        </div>
      </div>
    </main>
  );
}
