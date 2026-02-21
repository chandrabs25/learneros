"use client";

import { useEffect, useMemo, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type InsightItem = {
  id: string;
  type: "COMPETENCY" | "PARTIAL_UNDERSTANDING" | "MISCONCEPTION" | string;
  category: string;
  content: string;
  is_active: boolean;
  created_at?: string;
  concept_name?: string;
  source_title?: string;
  supersedes_ids?: string[];
};

type StudentDetail = {
  student: { student_id: string; name?: string; email?: string; institute_id?: string };
  risk: { risk_score: number; risk_band: "LOW" | "MEDIUM" | "HIGH" | string; reasons: string[] };
  active_counts: { competency: number; partial_understanding: number; misconception: number };
  active_insights: InsightItem[];
  timeline: InsightItem[];
};

function styleForType(type: string) {
  if (type === "MISCONCEPTION") return { bg: "#ffe7e7", fg: "#ef4444" };
  if (type === "PARTIAL_UNDERSTANDING") return { bg: "#fff6cc", fg: "#ca8a04" };
  return { bg: "#dcfce7", fg: "#16a34a" };
}

function riskStyle(risk: string) {
  if (risk === "HIGH") return { bg: "#ffe7e7", fg: "#ef4444" };
  if (risk === "MEDIUM") return { bg: "#fff6cc", fg: "#ca8a04" };
  return { bg: "#dcfce7", fg: "#16a34a" };
}

function timeAgo(value?: string): string {
  if (!value) return "No time";
  const dt = new Date(value);
  if (Number.isNaN(dt.getTime())) return value;
  const sec = Math.max(0, Math.floor((Date.now() - dt.getTime()) / 1000));
  if (sec < 60) return `${sec}s ago`;
  if (sec < 3600) return `${Math.floor(sec / 60)}m ago`;
  if (sec < 86400) return `${Math.floor(sec / 3600)}h ago`;
  return `${Math.floor(sec / 86400)}d ago`;
}

export default function TeacherStudentDetailPage() {
  const { studentId } = useParams<{ studentId: string }>();
  const router = useRouter();
  const { getIdToken } = useAuth();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [data, setData] = useState<StudentDetail | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      if (!studentId) return;
      setLoading(true);
      setError("");
      try {
        const token = await getIdToken();
        if (!token) {
          router.push("/auth");
          return;
        }
        const normalizedStudentId = decodeURIComponent(String(studentId));
        const res = await fetch(`${API_URL}/api/teachers/me/dashboard/students/${encodeURIComponent(normalizedStudentId)}`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        const j = await res.json();
        if (!res.ok) throw new Error(j?.detail || "Failed to load student");
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
  }, [getIdToken, router, studentId]);

  const risk = data?.risk.risk_band || "LOW";
  const riskChip = riskStyle(risk);

  const timelineSorted = useMemo(() => {
    const list = data?.timeline || [];
    return [...list].sort((a, b) => {
      const at = a.created_at ? new Date(a.created_at).getTime() : 0;
      const bt = b.created_at ? new Date(b.created_at).getTime() : 0;
      return bt - at;
    });
  }, [data]);

  return (
    <main style={{ background: "#f5f8f8", minHeight: "calc(100vh - 72px)", padding: "1.2rem 1.6rem 2rem" }}>
      <div style={{ maxWidth: 1280, margin: "0 auto", display: "flex", flexDirection: "column", gap: "1rem" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "0.7rem" }}>
          <button
            onClick={() => router.push("/teacher/dashboard/students")}
            style={{ border: "1px solid #cbd5e1", background: "#fff", borderRadius: 10, padding: "0.42rem 0.7rem", width: "fit-content", fontWeight: 700, cursor: "pointer" }}
          >
            Back to Students
          </button>
          {data?.student?.institute_id && (
            <div style={{ color: "#64748b", fontWeight: 700 }}>Institute: {data.student.institute_id}</div>
          )}
        </div>

        {error && (
          <div style={{ color: "#be123c", background: "#fff1f2", border: "1px solid #fecdd3", borderRadius: 10, padding: "0.7rem 0.9rem", fontWeight: 700 }}>
            {error}
          </div>
        )}

        {loading && <div style={{ color: "#64748b", fontWeight: 700 }}>Loading student profile...</div>}

        {data && (
          <>
            <section style={{ background: "#fff", border: "1px solid #e2e8f0", borderRadius: 14, padding: "1rem" }}>
              <h1 style={{ margin: 0 }}>{data.student.name || data.student.student_id}</h1>
              <div style={{ marginTop: 4, color: "#64748b", fontWeight: 600 }}>{data.student.email || data.student.student_id}</div>
              <div style={{ marginTop: 10, display: "flex", gap: "0.6rem", flexWrap: "wrap", alignItems: "center" }}>
                <span style={{ background: riskChip.bg, color: riskChip.fg, borderRadius: 999, padding: "0.2rem 0.6rem", fontWeight: 800, fontSize: "0.78rem", textTransform: "uppercase", letterSpacing: "0.08em" }}>
                  {data.risk.risk_band} Risk
                </span>
                <span style={{ background: "#e2e8f0", borderRadius: 999, padding: "0.2rem 0.6rem", fontWeight: 800, fontSize: "0.78rem" }}>
                  Score {data.risk.risk_score}
                </span>
              </div>
              {(data.risk.reasons || []).length > 0 && (
                <div style={{ marginTop: "0.75rem", color: "#334155", fontWeight: 700, fontSize: "0.88rem" }}>
                  Reason codes: {(data.risk.reasons || []).join(", ")}
                </div>
              )}
            </section>

            <section style={{ display: "grid", gridTemplateColumns: "repeat(4, minmax(0,1fr))", gap: "0.9rem" }}>
              <div style={{ background: "#fff", border: "1px solid #e2e8f0", borderRadius: 14, padding: "0.9rem 1rem" }}>
                <div style={{ color: "#64748b", fontWeight: 600, fontSize: "0.92rem" }}>Competencies</div>
                <div style={{ fontSize: "2rem", fontWeight: 800, marginTop: "0.35rem" }}>{data.active_counts.competency}</div>
              </div>
              <div style={{ background: "#fff", border: "1px solid #e2e8f0", borderRadius: 14, padding: "0.9rem 1rem" }}>
                <div style={{ color: "#64748b", fontWeight: 600, fontSize: "0.92rem" }}>Partial Understanding</div>
                <div style={{ fontSize: "2rem", fontWeight: 800, marginTop: "0.35rem" }}>{data.active_counts.partial_understanding}</div>
              </div>
              <div style={{ background: "#fff", border: "1px solid #e2e8f0", borderRadius: 14, padding: "0.9rem 1rem" }}>
                <div style={{ color: "#64748b", fontWeight: 600, fontSize: "0.92rem" }}>Misconceptions</div>
                <div style={{ fontSize: "2rem", fontWeight: 800, marginTop: "0.35rem" }}>{data.active_counts.misconception}</div>
              </div>
              <div style={{ background: "#fff", border: "1px solid #e2e8f0", borderRadius: 14, padding: "0.9rem 1rem" }}>
                <div style={{ color: "#64748b", fontWeight: 600, fontSize: "0.92rem" }}>Active Insights</div>
                <div style={{ fontSize: "2rem", fontWeight: 800, marginTop: "0.35rem" }}>{(data.active_insights || []).length}</div>
              </div>
            </section>

            <section style={{ display: "grid", gridTemplateColumns: "1.1fr 1.4fr", gap: "0.9rem" }}>
              <div style={{ background: "#fff", border: "1px solid #e2e8f0", borderRadius: 14, padding: "1rem", display: "flex", flexDirection: "column", gap: "0.65rem" }}>
                <h2 style={{ margin: 0, fontSize: "1.1rem" }}>Active Insights</h2>
                {(data.active_insights || []).map((ins) => {
                  const cs = styleForType(ins.type);
                  return (
                    <article key={ins.id} style={{ border: "1px solid #e2e8f0", borderRadius: 10, padding: "0.7rem 0.75rem" }}>
                      <div style={{ display: "flex", alignItems: "center", gap: "0.45rem", flexWrap: "wrap" }}>
                        <span style={{ background: cs.bg, color: cs.fg, borderRadius: 999, padding: "0.15rem 0.5rem", fontWeight: 800, fontSize: "0.68rem", letterSpacing: "0.08em" }}>
                          {ins.type.replaceAll("_", " ")}
                        </span>
                        <span style={{ color: "#94a3b8", fontWeight: 700, fontSize: "0.78rem" }}>{ins.category}</span>
                      </div>
                      <div style={{ marginTop: 6, color: "#1e293b", lineHeight: 1.45 }}>{ins.content}</div>
                      <div style={{ marginTop: 6, color: "#64748b", fontWeight: 600, fontSize: "0.78rem" }}>
                        {ins.concept_name || ins.source_title || "General"} • {timeAgo(ins.created_at)}
                      </div>
                    </article>
                  );
                })}
                {(data.active_insights || []).length === 0 && <div style={{ color: "#64748b" }}>No active insights yet.</div>}
              </div>

              <div style={{ background: "#fff", border: "1px solid #e2e8f0", borderRadius: 14, padding: "1rem" }}>
                <h2 style={{ marginTop: 0, marginBottom: "0.8rem", fontSize: "1.1rem" }}>Insight Timeline</h2>
                <div style={{ display: "flex", flexDirection: "column", gap: "0.65rem", maxHeight: 620, overflowY: "auto", paddingRight: "0.25rem" }}>
                  {timelineSorted.map((t) => {
                    const s = styleForType(t.type);
                    return (
                      <article key={t.id} style={{ border: "1px solid #e2e8f0", borderRadius: 10, padding: "0.7rem 0.8rem", background: t.is_active ? "#f8fafc" : "#fff" }}>
                        <div style={{ display: "flex", alignItems: "center", gap: "0.45rem", flexWrap: "wrap" }}>
                          <span style={{ background: s.bg, color: s.fg, borderRadius: 999, padding: "0.15rem 0.5rem", fontWeight: 800, fontSize: "0.68rem", letterSpacing: "0.08em" }}>
                            {t.type.replaceAll("_", " ")}
                          </span>
                          <span style={{ color: "#94a3b8", fontWeight: 700, fontSize: "0.78rem" }}>{t.category}</span>
                          {!t.is_active && (
                            <span style={{ background: "#f1f5f9", color: "#475569", borderRadius: 999, padding: "0.13rem 0.45rem", fontWeight: 800, fontSize: "0.66rem", letterSpacing: "0.08em" }}>
                              SUPERSEDED
                            </span>
                          )}
                          <span style={{ color: "#64748b", fontWeight: 600, fontSize: "0.78rem" }}>
                            {t.concept_name || t.source_title || "General"}
                          </span>
                          <span style={{ marginLeft: "auto", color: "#94a3b8", fontWeight: 700, fontSize: "0.74rem" }}>{timeAgo(t.created_at)}</span>
                        </div>
                        <div style={{ marginTop: 6, color: "#1e293b", lineHeight: 1.5 }}>{t.content}</div>
                        {!!(t.supersedes_ids || []).length && (
                          <div style={{ marginTop: 6, color: "#94a3b8", fontWeight: 700, fontSize: "0.72rem" }}>
                            Supersedes: {(t.supersedes_ids || []).length} prior insight(s)
                          </div>
                        )}
                      </article>
                    );
                  })}
                  {timelineSorted.length === 0 && <div style={{ color: "#64748b" }}>No insight timeline yet.</div>}
                </div>
              </div>
            </section>
          </>
        )}
      </div>

      <style jsx>{`
        @media (max-width: 1200px) {
          main section[style*="repeat(4"] {
            grid-template-columns: repeat(2, minmax(0, 1fr)) !important;
          }
          main section[style*="1.1fr 1.4fr"] {
            grid-template-columns: 1fr !important;
          }
        }
      `}</style>
    </main>
  );
}
