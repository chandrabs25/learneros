"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type ClusterMember = {
  student_id: string;
  name: string;
  email?: string;
  risk_score: number;
  risk_band: "LOW" | "MEDIUM" | "HIGH";
  reasons: string[];
  cluster_confidence?: number | null;
  cluster_distance?: number | null;
};

type RepresentativeInsight = {
  insight_id: string;
  student_id: string;
  type: string;
  content: string;
  concept_id?: string;
  concept_name?: string;
  source_id?: string;
  source_title?: string;
  created_at?: string;
};

type ClusterDetailResponse = {
  snapshot_id: string;
  run_at?: string;
  algorithm?: string;
  engine_version?: string;
  cluster: {
    cluster_id: string;
    label: string;
    size: number;
    avg_risk: number;
    is_noise_cluster: boolean;
    top_concepts: Array<{ id: string; name: string; count: number }>;
    top_terms: Array<{ term: string; count: number; kind: string }>;
    risk_band_counts: Record<string, number>;
    top_misconceptions: Array<{
      statement: string;
      count: number;
      concept_name?: string;
      source_title?: string;
    }>;
  };
  member_count_by_risk_band: Record<string, number>;
  representative_insights: RepresentativeInsight[];
  recommended_actions: string[];
  members: ClusterMember[];
};

function riskStyle(risk: string) {
  if (risk === "HIGH") return { bg: "#ffe7e7", fg: "#ef4444" };
  if (risk === "MEDIUM") return { bg: "#fff6cc", fg: "#ca8a04" };
  return { bg: "#dcfce7", fg: "#16a34a" };
}

function timeAgo(value?: string): string {
  if (!value) return "";
  const dt = new Date(value);
  if (Number.isNaN(dt.getTime())) return value;
  const sec = Math.max(0, Math.floor((Date.now() - dt.getTime()) / 1000));
  if (sec < 60) return `${sec}s ago`;
  if (sec < 3600) return `${Math.floor(sec / 60)}m ago`;
  if (sec < 86400) return `${Math.floor(sec / 3600)}h ago`;
  return `${Math.floor(sec / 86400)}d ago`;
}

export default function ClusterDetailPage() {
  const { clusterId } = useParams<{ clusterId: string }>();
  const router = useRouter();
  const { getIdToken, role, loading: authLoading } = useAuth();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [data, setData] = useState<ClusterDetailResponse | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      if (authLoading) return;
      if (role !== "teacher") {
        router.replace("/");
        return;
      }
      setLoading(true);
      setError("");
      try {
        const token = await getIdToken();
        if (!token) {
          router.push("/auth");
          return;
        }
        const decodedId = decodeURIComponent(String(clusterId));
        const res = await fetch(
          `${API_URL}/api/teachers/me/dashboard/clusters/${encodeURIComponent(decodedId)}?snapshot=latest`,
          { headers: { Authorization: `Bearer ${token}` } }
        );
        const j = await res.json();
        if (!res.ok) throw new Error(j?.detail || "Failed to load cluster");
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
  }, [getIdToken, router, clusterId, role, authLoading]);

  const cluster = data?.cluster;
  const riskCounts = data?.member_count_by_risk_band || {};
  const totalMembers = (riskCounts.HIGH || 0) + (riskCounts.MEDIUM || 0) + (riskCounts.LOW || 0) || 1;
  const maxConceptCount = Math.max(1, ...(cluster?.top_concepts || []).map((c) => c.count));

  return (
    <main style={{ background: "#f5f8f8", minHeight: "calc(100vh - 72px)", padding: "1.2rem 1.6rem 2rem" }}>
      <div style={{ maxWidth: 1360, margin: "0 auto", display: "flex", flexDirection: "column", gap: "1rem" }}>
        {/* Back button */}
        <button
          onClick={() => router.push("/teacher/dashboard")}
          style={{
            border: "1px solid #cbd5e1",
            background: "#fff",
            borderRadius: 10,
            padding: "0.42rem 0.7rem",
            width: "fit-content",
            fontWeight: 700,
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            gap: "0.35rem",
          }}
        >
          ← Back to Dashboard
        </button>

        {error && (
          <div style={{ color: "#be123c", background: "#fff1f2", border: "1px solid #fecdd3", borderRadius: 12, padding: "0.8rem 1rem", fontWeight: 700 }}>
            {error}
          </div>
        )}

        {loading && <div style={{ color: "#64748b", fontWeight: 700, padding: "2rem 0" }}>Loading cluster details…</div>}

        {data && cluster && (
          <>
            {/* Header */}
            <section style={{ background: "#fff", border: "1px solid #e2e8f0", borderRadius: 14, padding: "1.1rem 1.2rem" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "start", flexWrap: "wrap", gap: "0.8rem" }}>
                <div>
                  <h1 style={{ margin: 0, fontSize: "1.35rem", lineHeight: 1.3 }}>{cluster.label}</h1>
                  <div style={{ marginTop: 6, color: "#64748b", fontWeight: 600, fontSize: "0.88rem" }}>
                    {cluster.size} student{cluster.size !== 1 ? "s" : ""} • Avg risk: {cluster.avg_risk.toFixed(1)}
                    {cluster.is_noise_cluster && (
                      <span style={{ marginLeft: 8, background: "#f1f5f9", color: "#475569", borderRadius: 999, padding: "0.15rem 0.5rem", fontWeight: 800, fontSize: "0.7rem" }}>
                        NOISE CLUSTER
                      </span>
                    )}
                  </div>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", fontSize: "0.82rem", fontWeight: 700 }}>
                  <span style={{ color: "#94a3b8" }}>
                    {data.algorithm} • {data.engine_version}
                    {data.run_at ? ` • ${timeAgo(data.run_at)}` : ""}
                  </span>
                </div>
              </div>

              {/* Risk distribution bar */}
              <div style={{ marginTop: "0.9rem" }}>
                <div style={{ fontSize: "0.72rem", color: "#94a3b8", fontWeight: 800, textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 6 }}>
                  Risk Distribution
                </div>
                <div style={{ display: "flex", width: "100%", height: 12, borderRadius: 999, overflow: "hidden", background: "#e2e8f0" }}>
                  {(riskCounts.HIGH || 0) > 0 && (
                    <div style={{ width: `${((riskCounts.HIGH || 0) / totalMembers) * 100}%`, background: "#f87171" }} />
                  )}
                  {(riskCounts.MEDIUM || 0) > 0 && (
                    <div style={{ width: `${((riskCounts.MEDIUM || 0) / totalMembers) * 100}%`, background: "#facc15" }} />
                  )}
                  {(riskCounts.LOW || 0) > 0 && (
                    <div style={{ width: `${((riskCounts.LOW || 0) / totalMembers) * 100}%`, background: "#34d399" }} />
                  )}
                </div>
                <div style={{ display: "flex", gap: "1rem", marginTop: 6, fontSize: "0.78rem", fontWeight: 700 }}>
                  <span style={{ color: "#ef4444" }}>High: {riskCounts.HIGH || 0}</span>
                  <span style={{ color: "#ca8a04" }}>Medium: {riskCounts.MEDIUM || 0}</span>
                  <span style={{ color: "#16a34a" }}>Low: {riskCounts.LOW || 0}</span>
                </div>
              </div>
            </section>

            {/* 3-column body */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "0.9rem" }}>
              {/* Recommended Actions */}
              <section style={{ background: "#fff", border: "1px solid #e2e8f0", borderRadius: 14, padding: "1rem", display: "flex", flexDirection: "column", gap: "0.6rem" }}>
                <h2 style={{ margin: 0, fontSize: "1.05rem", display: "flex", alignItems: "center", gap: "0.4rem" }}>
                  <span style={{ fontSize: "1.1rem" }}>📋</span> Recommended Actions
                </h2>
                {(data.recommended_actions || []).length === 0 && (
                  <div style={{ color: "#94a3b8", fontWeight: 600 }}>No actions generated yet.</div>
                )}
                {(data.recommended_actions || []).map((action, i) => (
                  <div
                    key={i}
                    style={{
                      display: "flex",
                      gap: "0.55rem",
                      padding: "0.65rem 0.75rem",
                      background: "#f0fdfa",
                      border: "1px solid #ccfbf1",
                      borderRadius: 10,
                      fontSize: "0.88rem",
                      lineHeight: 1.45,
                      fontWeight: 600,
                      color: "#134e4a",
                    }}
                  >
                    <span style={{ flexShrink: 0, fontSize: "1rem" }}>
                      {i === 0 ? "🎯" : i === 1 ? "📝" : "🔁"}
                    </span>
                    <span>{action}</span>
                  </div>
                ))}
              </section>

              {/* Top Misconceptions */}
              <section style={{ background: "#fff", border: "1px solid #e2e8f0", borderRadius: 14, padding: "1rem", display: "flex", flexDirection: "column", gap: "0.6rem" }}>
                <h2 style={{ margin: 0, fontSize: "1.05rem", display: "flex", alignItems: "center", gap: "0.4rem" }}>
                  <span style={{ fontSize: "1.1rem" }}>⚠️</span> Top Misconceptions
                </h2>
                {(data.representative_insights || []).filter((i) => i.type === "MISCONCEPTION").length === 0 &&
                  (cluster.top_misconceptions || []).length === 0 && (
                    <div style={{ color: "#94a3b8", fontWeight: 600 }}>No misconceptions found.</div>
                  )}
                {(cluster.top_misconceptions || []).map((m, i) => (
                  <div
                    key={i}
                    style={{
                      padding: "0.6rem 0.7rem",
                      background: "#fff5f5",
                      border: "1px solid #fecaca",
                      borderRadius: 10,
                    }}
                  >
                    <div style={{ fontSize: "0.85rem", lineHeight: 1.45, color: "#1e293b" }}>
                      &ldquo;{m.statement}&rdquo;
                    </div>
                    <div style={{ marginTop: 5, display: "flex", gap: "0.5rem", flexWrap: "wrap", fontSize: "0.72rem", fontWeight: 700 }}>
                      <span style={{ color: "#ef4444" }}>{m.count} student{m.count !== 1 ? "s" : ""}</span>
                      {m.concept_name && (
                        <span style={{ color: "#64748b" }}>• {m.concept_name}</span>
                      )}
                      {m.source_title && (
                        <span style={{ color: "#94a3b8" }}>• {m.source_title}</span>
                      )}
                    </div>
                  </div>
                ))}
              </section>

              {/* Member List */}
              <section style={{ background: "#fff", border: "1px solid #e2e8f0", borderRadius: 14, padding: "1rem", display: "flex", flexDirection: "column", gap: "0.4rem" }}>
                <h2 style={{ margin: 0, fontSize: "1.05rem", display: "flex", alignItems: "center", gap: "0.4rem" }}>
                  <span style={{ fontSize: "1.1rem" }}>👥</span> Members ({data.members?.length || 0})
                </h2>
                <div style={{ maxHeight: 420, overflowY: "auto", display: "flex", flexDirection: "column", gap: "0.35rem", paddingRight: "0.2rem" }}>
                  {(data.members || []).map((m) => {
                    const rs = riskStyle(m.risk_band);
                    return (
                      <div
                        key={m.student_id}
                        onClick={() => router.push(`/teacher/dashboard/students/${encodeURIComponent(m.student_id)}`)}
                        style={{
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "space-between",
                          padding: "0.5rem 0.6rem",
                          border: "1px solid #f1f5f9",
                          borderRadius: 8,
                          cursor: "pointer",
                          transition: "background 120ms ease",
                        }}
                        onMouseEnter={(e) => (e.currentTarget.style.background = "#f8fafc")}
                        onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
                      >
                        <div>
                          <div style={{ fontWeight: 700, fontSize: "0.88rem" }}>{m.name}</div>
                          {m.email && <div style={{ color: "#94a3b8", fontSize: "0.75rem" }}>{m.email}</div>}
                        </div>
                        <div style={{ display: "flex", alignItems: "center", gap: "0.4rem" }}>
                          <span style={{ fontWeight: 800, fontSize: "0.78rem", color: "#64748b" }}>
                            {m.risk_score.toFixed(1)}
                          </span>
                          <span
                            style={{
                              background: rs.bg,
                              color: rs.fg,
                              borderRadius: 999,
                              padding: "0.13rem 0.45rem",
                              fontWeight: 800,
                              fontSize: "0.65rem",
                              textTransform: "uppercase",
                              letterSpacing: "0.08em",
                            }}
                          >
                            {m.risk_band}
                          </span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </section>
            </div>

            {/* Top Concepts + Key Terms */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.9rem" }}>
              {/* Top Concepts */}
              <section style={{ background: "#fff", border: "1px solid #e2e8f0", borderRadius: 14, padding: "1rem" }}>
                <h2 style={{ margin: 0, fontSize: "1.05rem", marginBottom: "0.75rem" }}>Top Concepts</h2>
                <div style={{ display: "flex", flexDirection: "column", gap: "0.7rem" }}>
                  {(cluster.top_concepts || []).slice(0, 6).map((c) => {
                    const pct = Math.round((c.count / maxConceptCount) * 100);
                    return (
                      <div key={c.id}>
                        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4, fontSize: "0.88rem" }}>
                          <span style={{ fontWeight: 700 }}>{c.name || c.id}</span>
                          <span style={{ color: "#64748b", fontWeight: 700 }}>{c.count}</span>
                        </div>
                        <div style={{ height: 8, background: "#e2e8f0", borderRadius: 999, overflow: "hidden" }}>
                          <div style={{ width: `${pct}%`, height: "100%", background: "#22d3ee", borderRadius: 999 }} />
                        </div>
                      </div>
                    );
                  })}
                  {(cluster.top_concepts || []).length === 0 && (
                    <div style={{ color: "#94a3b8", fontWeight: 600 }}>No concept data available.</div>
                  )}
                </div>
              </section>

              {/* Key Terms */}
              <section style={{ background: "#fff", border: "1px solid #e2e8f0", borderRadius: 14, padding: "1rem" }}>
                <h2 style={{ margin: 0, fontSize: "1.05rem", marginBottom: "0.75rem" }}>Key Terms</h2>
                <div style={{ display: "flex", flexWrap: "wrap", gap: "0.4rem" }}>
                  {(cluster.top_terms || []).map((t, i) => (
                    <span
                      key={i}
                      style={{
                        background: t.kind === "bigram" ? "#e0f2fe" : "#f1f5f9",
                        color: t.kind === "bigram" ? "#0369a1" : "#334155",
                        borderRadius: 999,
                        padding: "0.28rem 0.6rem",
                        fontWeight: 700,
                        fontSize: "0.82rem",
                      }}
                    >
                      {t.term}
                      <span style={{ marginLeft: 4, opacity: 0.6 }}>×{t.count}</span>
                    </span>
                  ))}
                  {(cluster.top_terms || []).length === 0 && (
                    <div style={{ color: "#94a3b8", fontWeight: 600 }}>No terms extracted.</div>
                  )}
                </div>
              </section>
            </div>
          </>
        )}
      </div>

      <style jsx>{`
        @media (max-width: 1100px) {
          main div[style*="grid-template-columns: 1fr 1fr 1fr"] {
            grid-template-columns: 1fr !important;
          }
          main div[style*="grid-template-columns: 1fr 1fr"] {
            grid-template-columns: 1fr !important;
          }
        }
      `}</style>
    </main>
  );
}
