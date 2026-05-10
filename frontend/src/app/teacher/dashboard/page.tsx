"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type OverviewResponse = {
  institute_id: string;
  grade?: number | null;
  window: "7d" | "30d" | "90d";
  totals: {
    students: number;
    competency: number;
    partial_understanding: number;
    misconception: number;
    high_risk_students: number;
  };
  trends: {
    insights: { current: number; previous: number; delta: number };
    misconception: { current: number; previous: number; delta: number };
  };
  top_misconceptions: {
    concepts: Array<{ concept_id: string; concept_name: string; count: number }>;
    sources: Array<{ source_id: string; source_title: string; count: number }>;
  };
};

type StudentRow = {
  student_id: string;
  name: string;
  email?: string;
  grade?: number | null;
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

type ClustersResponse = {
  snapshot_id: string | null;
  clusters: Array<{
    cluster_id: string;
    label: string;
    size: number;
    avg_risk: number;
    top_concepts?: Array<{ id: string; name: string; count: number }>;
    risk_band_counts?: Record<string, number>;
  }>;
};

type ClusterTrendsResponse = {
  snapshots: Array<{
    snapshot_id: string;
    run_at: string;
    algorithm: string;
    student_count: number;
    noise_students: number;
    cluster_count: number;
    k: number;
    silhouette: number;
    high_risk_count: number;
    medium_risk_count: number;
    low_risk_count: number;
  }>;
  columns: Array<{
    snapshot_id: string;
    run_at: string;
    clusters: Array<{
      cluster_id: string;
      label: string;
      size: number;
      avg_risk: number;
    }>;
  }>;
  flows: Array<{
    from_snapshot: string;
    to_snapshot: string;
    from_cluster_id: string;
    from_label: string;
    to_cluster_id: string;
    to_label: string;
    count: number;
    direction: "improved" | "declined" | "stable" | "lateral";
  }>;
  migrations: Array<{
    student_name: string;
    from_cluster_label: string;
    to_cluster_label: string;
    direction: "improved" | "declined" | "lateral" | "stable";
  }>;
  summary: {
    total_snapshots: number;
    students_improved: number;
    students_declined: number;
    students_stable: number;
  };
};

type SubjectOption = {
  id: string;
  name: string;
};

function timeAgo(value?: string | null): string {
  if (!value) return "No activity";
  const dt = new Date(value);
  const sec = Math.max(0, Math.floor((Date.now() - dt.getTime()) / 1000));
  if (sec < 60) return `${sec}s ago`;
  if (sec < 3600) return `${Math.floor(sec / 60)}m ago`;
  if (sec < 86400) return `${Math.floor(sec / 3600)}h ago`;
  return `${Math.floor(sec / 86400)}d ago`;
}

function riskChip(risk: string) {
  if (risk === "HIGH") return { bg: "#ffe7e7", color: "#ef4444", label: "High Risk" };
  if (risk === "MEDIUM") return { bg: "#fff6cc", color: "#ca8a04", label: "Moderate" };
  return { bg: "#dcfce7", color: "#16a34a", label: "Low" };
}

function sparkPath(values: number[]) {
  if (!values.length) return "M0 10 L100 10";
  const step = 100 / Math.max(1, values.length - 1);
  const max = Math.max(...values, 1);
  return values
    .map((v, i) => {
      const x = i * step;
      const y = 18 - (v / max) * 14;
      return `${i === 0 ? "M" : "L"}${x} ${y}`;
    })
    .join(" ");
}

export default function TeacherDashboardPage() {
  const router = useRouter();
  const { user, getIdToken, role, loading: authLoading } = useAuth();

  const [windowDays, setWindowDays] = useState<"7d" | "30d" | "90d">("30d");
  const [riskFilter, setRiskFilter] = useState<"" | "HIGH" | "MEDIUM" | "LOW">("");
  const [gradeFilter, setGradeFilter] = useState<"" | `${number}`>("");
  const [textbookGradeFilter, setTextbookGradeFilter] = useState<"" | `${number}`>("");
  const [subjectFilter, setSubjectFilter] = useState("");
  const [subjects, setSubjects] = useState<SubjectOption[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [overview, setOverview] = useState<OverviewResponse | null>(null);
  const [students, setStudents] = useState<StudentsResponse | null>(null);
  const [clusters, setClusters] = useState<ClustersResponse | null>(null);
  const [clusterTrends, setClusterTrends] = useState<ClusterTrendsResponse | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError("");
      try {
        if (authLoading) return;
        const token = await getIdToken();
        if (!token) {
          router.push("/auth");
          return;
        }
        const headers = { Authorization: `Bearer ${token}` };
        if (role === "admin" || role === "superadmin") {
          router.replace("/admin/dashboard");
          return;
        }
        if (role !== "teacher") {
          router.replace("/");
          return;
        }

        const gradeQuery = gradeFilter ? `&grade=${encodeURIComponent(gradeFilter)}` : "";
        const textbookGradeQuery = textbookGradeFilter ? `&textbook_grade=${encodeURIComponent(textbookGradeFilter)}` : "";
        const subjectQuery = subjectFilter ? `&subject=${encodeURIComponent(subjectFilter)}` : "";
        const [oRes, sRes] = await Promise.all([
          fetch(`${API_URL}/api/teachers/me/dashboard/overview?window=${windowDays}${gradeQuery}${textbookGradeQuery}${subjectQuery}`, { headers }),
          fetch(
            `${API_URL}/api/teachers/me/dashboard/students?page=1&limit=8${riskFilter ? `&risk=${riskFilter}` : ""}${gradeQuery}${textbookGradeQuery}${subjectQuery}`,
            { headers }
          ),
        ]);

        const [oData, sData] = await Promise.all([oRes.json(), sRes.json()]);
        if (!oRes.ok) throw new Error(oData?.detail || "Failed to load overview");
        if (!sRes.ok) throw new Error(sData?.detail || "Failed to load students");

        if (!cancelled) {
          setOverview(oData);
          setStudents(sData);
        }
      } catch (e: unknown) {
        if (!cancelled) setError(e instanceof Error ? e.message : "Failed to load dashboard");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [windowDays, riskFilter, gradeFilter, textbookGradeFilter, subjectFilter, getIdToken, router, user, role, authLoading]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        if (authLoading) return;
        if (role !== "teacher") return;
        const token = await getIdToken();
        if (!token) return;
        const headers = { Authorization: `Bearer ${token}` };
        const cRes = await fetch(`${API_URL}/api/teachers/me/dashboard/clusters?snapshot=latest`, { headers });
        const cData = await cRes.json();
        if (!cRes.ok) throw new Error(cData?.detail || "Failed to load clusters");
        if (!cancelled) setClusters(cData);
      } catch {
        if (!cancelled) setClusters(null);
      }
      // Also fetch cluster trends
      try {
        const token = await getIdToken();
        if (!token) return;
        const headers = { Authorization: `Bearer ${token}` };
        const tRes = await fetch(`${API_URL}/api/teachers/me/dashboard/cluster-trends?window=90d`, { headers });
        const tData = await tRes.json();
        if (!cancelled && tRes.ok) setClusterTrends(tData);
      } catch {
        // trends are non-critical, silently fail
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [getIdToken, role, authLoading]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      if (!textbookGradeFilter) {
        setSubjects([]);
        setSubjectFilter("");
        return;
      }
      try {
        const res = await fetch(`${API_URL}/api/grades/${textbookGradeFilter}/subjects`);
        const data = await res.json();
        if (!cancelled) {
          const list = (Array.isArray(data) ? data : [])
            .map((s) => ({ id: String(s?.id || s?.name || ""), name: String(s?.name || s?.id || "") }))
            .filter((s) => s.name);
          setSubjects(list);
          if (subjectFilter && !list.some((s) => s.name === subjectFilter)) {
            setSubjectFilter("");
          }
        }
      } catch {
        if (!cancelled) setSubjects([]);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [textbookGradeFilter, subjectFilter]);

  const clusterLegend = useMemo(() => {
    const list = clusters?.clusters || [];
    const total = list.reduce((acc, c) => acc + (c.size || 0), 0) || 1;
    const palette = ["#34d399", "#22d3ee", "#facc15", "#f87171", "#a78bfa", "#60a5fa"];
    return list.slice(0, 6).map((c, i) => ({
      ...c,
      color: palette[i % palette.length],
      pct: Math.round(((c.size || 0) / total) * 100),
    }));
  }, [clusters]);

  const misconceptionRows = (overview?.top_misconceptions?.concepts || []).slice(0, 6);
  const maxMisCount = Math.max(1, ...misconceptionRows.map((r) => r.count));
  const sourceHotspots = (overview?.top_misconceptions?.sources || []).slice(0, 12);
  const maxSourceCount = Math.max(1, ...sourceHotspots.map((r) => r.count));

  return (
    <main style={{ background: "#f5f8f8", minHeight: "calc(100vh - 72px)", padding: "1.4rem 1.6rem 2rem" }}>
      <div style={{ maxWidth: 1440, margin: "0 auto", display: "flex", flexDirection: "column", gap: "1rem" }}>
        <div style={{ display: "flex", flexWrap: "wrap", alignItems: "end", justifyContent: "space-between", gap: "0.7rem" }}>
          <div style={{ display: "flex", alignItems: "end", gap: "0.6rem", flexWrap: "wrap" }}>
            <div>
              <div style={{ fontSize: "0.65rem", color: "#94a3b8", letterSpacing: "0.08em", fontWeight: 800, textTransform: "uppercase" }}>Window</div>
              <select
                value={windowDays}
                onChange={(e) => setWindowDays(e.target.value as "7d" | "30d" | "90d")}
                style={{ padding: "0.55rem 0.8rem", borderRadius: 10, border: "1px solid #e2e8f0", background: "#fff", fontWeight: 700 }}
              >
                <option value="7d">Last 7 Days</option>
                <option value="30d">Last 30 Days</option>
                <option value="90d">Last 90 Days</option>
              </select>
            </div>
            <div>
              <div style={{ fontSize: "0.65rem", color: "#94a3b8", letterSpacing: "0.08em", fontWeight: 800, textTransform: "uppercase" }}>Grade</div>
              <select
                value={gradeFilter}
                onChange={(e) => setGradeFilter(e.target.value as "" | `${number}`)}
                style={{ padding: "0.55rem 0.8rem", borderRadius: 10, border: "1px solid #e2e8f0", background: "#fff", fontWeight: 700 }}
              >
                <option value="">All Grades</option>
                {Array.from({ length: 12 }, (_, i) => i + 1).map((g) => (
                  <option key={g} value={String(g)}>
                    Grade {g}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <div style={{ fontSize: "0.65rem", color: "#94a3b8", letterSpacing: "0.08em", fontWeight: 800, textTransform: "uppercase" }}>Textbook Grade</div>
              <select
                value={textbookGradeFilter}
                onChange={(e) => setTextbookGradeFilter(e.target.value as "" | `${number}`)}
                style={{ padding: "0.55rem 0.8rem", borderRadius: 10, border: "1px solid #e2e8f0", background: "#fff", fontWeight: 700 }}
              >
                <option value="">All Textbook Grades</option>
                {Array.from({ length: 12 }, (_, i) => i + 1).map((g) => (
                  <option key={g} value={String(g)}>
                    Grade {g}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <div style={{ fontSize: "0.65rem", color: "#94a3b8", letterSpacing: "0.08em", fontWeight: 800, textTransform: "uppercase" }}>Subject</div>
              <select
                value={subjectFilter}
                onChange={(e) => setSubjectFilter(e.target.value)}
                disabled={!textbookGradeFilter}
                style={{ padding: "0.55rem 0.8rem", borderRadius: 10, border: "1px solid #e2e8f0", background: "#fff", fontWeight: 700, minWidth: 180 }}
              >
                <option value="">{textbookGradeFilter ? "All Subjects" : "Select textbook grade first"}</option>
                {subjects.map((s) => (
                  <option key={s.id} value={s.name}>
                    {s.name}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <div style={{ fontSize: "0.65rem", color: "#94a3b8", letterSpacing: "0.08em", fontWeight: 800, textTransform: "uppercase" }}>Risk</div>
              <select
                value={riskFilter}
                onChange={(e) => setRiskFilter(e.target.value as "" | "HIGH" | "MEDIUM" | "LOW")}
                style={{ padding: "0.55rem 0.8rem", borderRadius: 10, border: "1px solid #e2e8f0", background: "#fff", fontWeight: 700 }}
              >
                <option value="">All Risk Levels</option>
                <option value="HIGH">High Risk</option>
                <option value="MEDIUM">Medium Risk</option>
                <option value="LOW">Low Risk</option>
              </select>
            </div>
          </div>
          <div style={{ color: "#64748b", fontSize: "0.85rem", fontWeight: 700 }}>
            Institute: {overview?.institute_id || "—"}
            {gradeFilter ? ` • Grade ${gradeFilter}` : ""}
            {textbookGradeFilter ? ` • Textbook Grade ${textbookGradeFilter}` : ""}
            {subjectFilter ? ` • ${subjectFilter}` : ""}
          </div>
        </div>

        {error && (
          <div style={{ background: "#fff1f2", border: "1px solid #fecdd3", color: "#be123c", borderRadius: 12, padding: "0.8rem 1rem", fontWeight: 700 }}>
            {error}
          </div>
        )}

        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, minmax(0,1fr))", gap: "0.9rem" }}>
          {[
            { title: "Total Students", value: overview?.totals?.students ?? 0, color: "#22d3ee", spark: [3, 5, 4, 6, 8] },
            {
              title: "Average Mastery",
              value:
                overview
                  ? `${Math.round((overview.totals.competency / Math.max(1, overview.totals.competency + overview.totals.partial_understanding + overview.totals.misconception)) * 100)}%`
                  : "0%",
              color: "#22d3ee",
              spark: [2, 3, 3, 7, 9],
            },
            { title: "Active Risks", value: overview?.totals?.high_risk_students ?? 0, color: "#f87171", spark: [8, 8, 7, 6, 4] },
            {
              title: "Concepts Flagged",
              value: overview?.top_misconceptions?.concepts?.length ?? 0,
              color: "#22d3ee",
              spark: [3, 3, 4, 3, 3],
            },
          ].map((card) => (
            <div key={card.title} style={{ background: "#fff", border: "1px solid #e2e8f0", borderRadius: 14, padding: "0.9rem 1rem" }}>
              <div style={{ color: "#64748b", fontWeight: 600, fontSize: "0.92rem" }}>{card.title}</div>
              <div style={{ fontSize: "2rem", fontWeight: 800, marginTop: "0.4rem" }}>{loading ? "…" : card.value}</div>
              <svg viewBox="0 0 100 20" style={{ width: "100%", height: 34, marginTop: 8 }}>
                <path d={sparkPath(card.spark)} fill="none" stroke={card.color} strokeWidth={2.2} />
              </svg>
            </div>
          ))}
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: "0.9rem" }}>
          <div style={{ background: "#fff", border: "1px solid #e2e8f0", borderRadius: 14, overflow: "hidden" }}>
            <div style={{ padding: "0.9rem 1rem", borderBottom: "1px solid #f1f5f9", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <h2 style={{ margin: 0, fontSize: "1.1rem" }}>Student Risk Monitoring</h2>
              <button
                onClick={() => {
                  const q = new URLSearchParams();
                  if (riskFilter) q.set("risk", riskFilter);
                  if (gradeFilter) q.set("grade", gradeFilter);
                  if (textbookGradeFilter) q.set("textbook_grade", textbookGradeFilter);
                  if (subjectFilter) q.set("subject", subjectFilter);
                  const query = q.toString();
                  router.push(`/teacher/dashboard/students${query ? `?${query}` : ""}`);
                }}
                style={{ border: "none", background: "transparent", color: "#06b6d4", fontWeight: 800, cursor: "pointer" }}
              >
                View All Students
              </button>
            </div>
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse" }}>
                <thead style={{ background: "#f8fafc", fontSize: "0.72rem", color: "#64748b", textTransform: "uppercase", letterSpacing: "0.08em" }}>
                  <tr>
                    <th style={{ textAlign: "left", padding: "0.75rem 1rem" }}>Student</th>
                    <th style={{ textAlign: "left", padding: "0.75rem 1rem" }}>Risk</th>
                    <th style={{ textAlign: "left", padding: "0.75rem 1rem" }}>Last Activity</th>
                    <th style={{ textAlign: "right", padding: "0.75rem 1rem" }}>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {(students?.items || []).map((s) => {
                    const chip = riskChip(s.risk_band);
                    return (
                      <tr key={s.student_id} style={{ borderTop: "1px solid #f1f5f9" }}>
                        <td style={{ padding: "0.75rem 1rem", fontWeight: 700 }}>{s.name}</td>
                        <td style={{ padding: "0.75rem 1rem" }}>
                          <span style={{ background: chip.bg, color: chip.color, borderRadius: 999, padding: "0.2rem 0.55rem", fontWeight: 800, fontSize: "0.7rem", letterSpacing: "0.08em", textTransform: "uppercase" }}>{chip.label}</span>
                        </td>
                        <td style={{ padding: "0.75rem 1rem", color: "#64748b", fontWeight: 600 }}>{timeAgo(s.last_activity)}</td>
                        <td style={{ padding: "0.75rem 1rem", textAlign: "right" }}>
                          <button
                            onClick={() => router.push(`/teacher/dashboard/students/${encodeURIComponent(s.student_id)}`)}
                            style={{ border: "none", background: "transparent", cursor: "pointer" }}
                          >
                            <span className="material-symbols-outlined" style={{ fontSize: 20 }}>visibility</span>
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                  {!loading && (students?.items || []).length === 0 && (
                    <tr>
                      <td colSpan={4} style={{ padding: "1rem", color: "#64748b", textAlign: "center", fontWeight: 600 }}>
                        No students found for this filter.
                      </td>
                    </tr>
                  )}
                  {loading && [1, 2, 3].map((k) => (
                    <tr key={`sk-${k}`} style={{ borderTop: "1px solid #f1f5f9" }}>
                      <td style={{ padding: "0.9rem 1rem" }}><div style={{ height: 12, width: 140, background: "#e2e8f0", borderRadius: 8 }} /></td>
                      <td style={{ padding: "0.9rem 1rem" }}><div style={{ height: 12, width: 84, background: "#e2e8f0", borderRadius: 999 }} /></td>
                      <td style={{ padding: "0.9rem 1rem" }}><div style={{ height: 12, width: 96, background: "#e2e8f0", borderRadius: 8 }} /></td>
                      <td style={{ padding: "0.9rem 1rem", textAlign: "right" }}><div style={{ height: 12, width: 22, background: "#e2e8f0", borderRadius: 8, marginLeft: "auto" }} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div style={{ background: "#fff", border: "1px solid #e2e8f0", borderRadius: 14, padding: "1rem", display: "flex", flexDirection: "column", gap: "0.7rem" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <h2 style={{ margin: 0, fontSize: "1.1rem" }}>Knowledge Clusters</h2>
              <div style={{ border: "6px solid #f1f5f9", borderRadius: 999, width: 56, height: 56, display: "grid", placeItems: "center" }}>
                <div style={{ textAlign: "center" }}>
                  <div style={{ fontSize: "1rem", fontWeight: 900, lineHeight: 1.1 }}>{Math.round((1 - (overview?.totals?.high_risk_students || 0) / Math.max(1, overview?.totals?.students || 1)) * 100)}</div>
                  <div style={{ fontSize: "0.5rem", color: "#64748b", fontWeight: 800, letterSpacing: "0.06em", textTransform: "uppercase" }}>Health</div>
                </div>
              </div>
            </div>
            {/* Stacked bar */}
            <div style={{ display: "flex", width: "100%", height: 10, borderRadius: 999, overflow: "hidden", background: "#e2e8f0" }}>
              {clusterLegend.map((c) => (
                <div key={c.cluster_id} style={{ width: `${Math.max(6, c.pct)}%`, background: c.color }} />
              ))}
            </div>
            {/* Cluster cards */}
            <div style={{ display: "flex", flexDirection: "column", gap: "0.4rem", overflowY: "auto", maxHeight: 280 }}>
              {clusterLegend.map((c) => {
                const rbc = (c as Record<string, unknown>).risk_band_counts as Record<string, number> | undefined;
                const topConcepts = ((c as Record<string, unknown>).top_concepts as Array<{ name: string }>) || [];
                return (
                  <div
                    key={`l-${c.cluster_id}`}
                    onClick={() => router.push(`/teacher/dashboard/clusters/${encodeURIComponent(c.cluster_id)}`)}
                    style={{ display: "flex", alignItems: "center", gap: "0.5rem", padding: "0.45rem 0.55rem", border: "1px solid #f1f5f9", borderRadius: 10, cursor: "pointer", transition: "background 120ms ease" }}
                    onMouseEnter={(e) => (e.currentTarget.style.background = "#f8fafc")}
                    onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
                  >
                    <span style={{ width: 10, height: 10, borderRadius: 999, background: c.color, flexShrink: 0 }} />
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ fontSize: "0.78rem", fontWeight: 700, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                        {c.label}
                      </div>
                      {topConcepts.length > 0 && (
                        <div style={{ fontSize: "0.68rem", color: "#94a3b8", fontWeight: 600, marginTop: 1 }}>
                          {topConcepts.slice(0, 2).map((tc) => tc.name).join(", ")}
                        </div>
                      )}
                    </div>
                    <div style={{ display: "flex", alignItems: "center", gap: "0.25rem", flexShrink: 0 }}>
                      {rbc && (rbc.HIGH || 0) > 0 && <span style={{ width: 6, height: 6, borderRadius: 999, background: "#f87171" }} title={`${rbc.HIGH} high risk`} />}
                      {rbc && (rbc.MEDIUM || 0) > 0 && <span style={{ width: 6, height: 6, borderRadius: 999, background: "#facc15" }} title={`${rbc.MEDIUM} medium risk`} />}
                      <span style={{ fontSize: "0.72rem", fontWeight: 800, color: "#64748b" }}>{c.size}</span>
                    </div>
                  </div>
                );
              })}
              {clusterLegend.length === 0 && !loading && (
                <div style={{ color: "#94a3b8", fontWeight: 600, fontSize: "0.85rem" }}>No clusters built yet.</div>
              )}
            </div>
          </div>
        </div>

        {/* Cluster Evolution – Alluvial Flow Diagram */}
        {clusterTrends && clusterTrends.columns && clusterTrends.columns.length >= 2 && (
          <div style={{ background: "#fff", border: "1px solid #e2e8f0", borderRadius: 14, padding: "1rem" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.7rem" }}>
              <h2 style={{ margin: 0, fontSize: "1.1rem", display: "flex", alignItems: "center", gap: "0.4rem" }}>
                <span style={{ fontSize: "1.1rem" }}>📈</span> Cluster Evolution
              </h2>
              <span style={{ color: "#94a3b8", fontWeight: 700, fontSize: "0.78rem" }}>
                {clusterTrends.columns.length} snapshots
              </span>
            </div>

            {/* Alluvial / Sankey diagram */}
            {(() => {
              const cols = clusterTrends.columns;
              const allFlows = clusterTrends.flows;

              // Layout constants
              const colW = 100;         // width of each cluster rect column
              const gap = 140;          // horizontal gap between columns for flow paths
              const svgW = cols.length * colW + (cols.length - 1) * gap;
              const unitH = 28;         // height per student in a cluster rect
              const clusterGap = 8;     // vertical gap between clusters in a column
              const padTop = 28;        // top padding for date labels

              // Colour by avg_risk
              const riskColor = (r: number) =>
                r >= 10 ? "#f87171" : r >= 5 ? "#facc15" : "#4ade80";

              // Build position map: { [cluster_id]: { x, y, w, h } }
              type Rect = { x: number; y: number; w: number; h: number; label: string; risk: number; size: number };
              const rectMap: Record<string, Rect> = {};
              let maxColH = 0;

              cols.forEach((col, ci) => {
                const x = ci * (colW + gap);
                let y = padTop;
                col.clusters.forEach((cl) => {
                  const h = Math.max(unitH, cl.size * unitH);
                  rectMap[cl.cluster_id] = { x, y, w: colW, h, label: cl.label, risk: cl.avg_risk, size: cl.size };
                  y += h + clusterGap;
                });
                if (y > maxColH) maxColH = y;
              });

              const svgH = maxColH + 16;

              // Flow colour
              const flowColor = (dir: string) =>
                dir === "improved" ? "rgba(74,222,128,0.35)" : dir === "declined" ? "rgba(248,113,113,0.35)" : "rgba(148,163,184,0.2)";
              const flowStroke = (dir: string) =>
                dir === "improved" ? "#16a34a" : dir === "declined" ? "#ef4444" : "#94a3b8";

              // Compute flow path offsets so they stack within each cluster rect
              // Build offset trackers per cluster_id side (left=outgoing, right=incoming)
              const outOffset: Record<string, number> = {};
              const inOffset: Record<string, number> = {};

              return (
                <div style={{ overflowX: "auto", marginBottom: "0.7rem" }}>
                  <svg width={svgW} height={svgH} style={{ display: "block", minWidth: svgW }}>
                    {/* Date labels */}
                    {cols.map((col, ci) => {
                      const x = ci * (colW + gap);
                      const date = col.run_at ? new Date(col.run_at) : null;
                      const label = date ? `${date.getMonth() + 1}/${date.getDate()}` : "";
                      return (
                        <text key={`d-${ci}`} x={x + colW / 2} y={14} textAnchor="middle" fontSize={11} fontWeight={700} fill="#94a3b8">
                          {label}
                        </text>
                      );
                    })}

                    {/* Flow paths (drawn first so rects overlap) */}
                    {allFlows.map((f, fi) => {
                      const from = rectMap[f.from_cluster_id];
                      const to = rectMap[f.to_cluster_id];
                      if (!from || !to) return null;

                      const thickness = Math.max(2, f.count * unitH * 0.8);

                      // Stack offsets
                      const oKey = f.from_cluster_id;
                      const iKey = f.to_cluster_id;
                      outOffset[oKey] = outOffset[oKey] || 0;
                      inOffset[iKey] = inOffset[iKey] || 0;

                      const y1 = from.y + outOffset[oKey] + thickness / 2;
                      const y2 = to.y + inOffset[iKey] + thickness / 2;
                      outOffset[oKey] += thickness + 1;
                      inOffset[iKey] += thickness + 1;

                      const x1 = from.x + from.w;
                      const x2 = to.x;
                      const cx = (x1 + x2) / 2;

                      return (
                        <path
                          key={`f-${fi}`}
                          d={`M ${x1} ${y1} C ${cx} ${y1}, ${cx} ${y2}, ${x2} ${y2}`}
                          fill="none"
                          stroke={f.direction === "stable" ? flowColor(f.direction) : flowStroke(f.direction)}
                          strokeWidth={thickness}
                          opacity={f.direction === "stable" ? 0.5 : 0.7}
                          strokeLinecap="round"
                        >
                          <title>{f.count} student{f.count !== 1 ? "s" : ""}: {f.from_label} → {f.to_label} ({f.direction})</title>
                        </path>
                      );
                    })}

                    {/* Cluster rectangles */}
                    {Object.entries(rectMap).map(([cid, r]) => (
                      <g key={cid}>
                        <rect x={r.x} y={r.y} width={r.w} height={r.h} rx={6} fill={riskColor(r.risk)} opacity={0.85} stroke="#fff" strokeWidth={1.5} />
                        <text x={r.x + r.w / 2} y={r.y + r.h / 2 - 4} textAnchor="middle" fontSize={9} fontWeight={800} fill="#0f172a">
                          {r.label.length > 16 ? r.label.slice(0, 14) + "…" : r.label}
                        </text>
                        <text x={r.x + r.w / 2} y={r.y + r.h / 2 + 8} textAnchor="middle" fontSize={9} fontWeight={700} fill="#334155">
                          {r.size} students
                        </text>
                      </g>
                    ))}
                  </svg>
                </div>
              );
            })()}

            {/* Migration summary badges */}
            <div style={{ display: "flex", gap: "0.5rem", marginBottom: "0.6rem", flexWrap: "wrap" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "0.3rem", background: "#dcfce7", border: "1px solid #bbf7d0", borderRadius: 999, padding: "0.25rem 0.6rem", fontSize: "0.78rem", fontWeight: 800, color: "#16a34a" }}>
                ↑ {clusterTrends.summary.students_improved} improved
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: "0.3rem", background: "#ffe7e7", border: "1px solid #fecaca", borderRadius: 999, padding: "0.25rem 0.6rem", fontSize: "0.78rem", fontWeight: 800, color: "#ef4444" }}>
                ↓ {clusterTrends.summary.students_declined} declined
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: "0.3rem", background: "#f1f5f9", border: "1px solid #e2e8f0", borderRadius: 999, padding: "0.25rem 0.6rem", fontSize: "0.78rem", fontWeight: 800, color: "#64748b" }}>
                → {clusterTrends.summary.students_stable} stable
              </div>
            </div>

            {/* Migration details */}
            {clusterTrends.migrations.length > 0 && (
              <div>
                <div style={{ fontSize: "0.68rem", color: "#94a3b8", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 6 }}>
                  Recent Movements
                </div>
                <div style={{ display: "flex", flexDirection: "column", gap: "0.3rem", maxHeight: 160, overflowY: "auto" }}>
                  {clusterTrends.migrations.slice(0, 10).map((m, i) => (
                    <div key={i} style={{ display: "flex", alignItems: "center", gap: "0.4rem", padding: "0.35rem 0.5rem", background: m.direction === "improved" ? "#f0fdf4" : m.direction === "declined" ? "#fff5f5" : "#f8fafc", border: `1px solid ${m.direction === "improved" ? "#bbf7d0" : m.direction === "declined" ? "#fecaca" : "#e2e8f0"}`, borderRadius: 8, fontSize: "0.78rem" }}>
                      <span style={{ fontWeight: 800, fontSize: "0.85rem" }}>
                        {m.direction === "improved" ? "↑" : m.direction === "declined" ? "↓" : "→"}
                      </span>
                      <span style={{ fontWeight: 700, color: "#334155" }}>{m.student_name}</span>
                      <span style={{ color: "#94a3b8", fontWeight: 600, fontSize: "0.72rem" }}>
                        {m.from_cluster_label} → {m.to_cluster_label}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.9rem" }}>
          <div style={{ background: "#fff", border: "1px solid #e2e8f0", borderRadius: 14, padding: "1rem" }}>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "1rem" }}>
              <h2 style={{ margin: 0, fontSize: "1.1rem" }}>Top Misconceptions</h2>
              <span style={{ color: "#94a3b8", fontWeight: 700, fontSize: "0.82rem" }}>Last {windowDays}</span>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: "0.9rem" }}>
              {misconceptionRows.map((r) => {
                const pct = Math.round((r.count / maxMisCount) * 100);
                return (
                  <div key={r.concept_id}>
                    <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6, fontSize: "0.92rem" }}>
                      <span style={{ fontWeight: 700 }}>{r.concept_name || r.concept_id}</span>
                      <span style={{ color: pct >= 60 ? "#ef4444" : pct >= 35 ? "#ca8a04" : "#16a34a", fontWeight: 800 }}>{pct}% signal</span>
                    </div>
                    <div style={{ height: 10, background: "#e2e8f0", borderRadius: 999, overflow: "hidden" }}>
                      <div style={{ width: `${pct}%`, height: "100%", background: "#22d3ee" }} />
                    </div>
                  </div>
                );
              })}
              {!loading && misconceptionRows.length === 0 && (
                <div style={{ color: "#64748b", fontWeight: 600 }}>No misconception trends available yet.</div>
              )}
            </div>
          </div>

          <div style={{ background: "#fff", border: "1px solid #e2e8f0", borderRadius: 14, padding: "1rem" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.75rem" }}>
              <h2 style={{ margin: 0, fontSize: "1.1rem" }}>Content Hotspots</h2>
              <div style={{ display: "flex", gap: "0.6rem", fontSize: "0.68rem", fontWeight: 700 }}>
                <span style={{ display: "flex", alignItems: "center", gap: "0.2rem" }}><span style={{ width: 8, height: 8, borderRadius: 2, background: "#f87171" }} />≥10</span>
                <span style={{ display: "flex", alignItems: "center", gap: "0.2rem" }}><span style={{ width: 8, height: 8, borderRadius: 2, background: "#facc15" }} />≥5</span>
                <span style={{ display: "flex", alignItems: "center", gap: "0.2rem" }}><span style={{ width: 8, height: 8, borderRadius: 2, background: "#34d399" }} />&lt;5</span>
              </div>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: "0.45rem" }}>
              {sourceHotspots.map((s, idx) => {
                const barPct = Math.max(4, Math.round((s.count / maxSourceCount) * 100));
                const barColor = s.count >= 10 ? "#f87171" : s.count >= 5 ? "#facc15" : "#34d399";
                const textColor = s.count >= 10 ? "#991b1b" : s.count >= 5 ? "#854d0e" : "#065f46";
                return (
                  <div key={`${s.source_id}-${idx}`} style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                    <div style={{ width: 130, fontSize: "0.78rem", fontWeight: 700, color: "#334155", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis", flexShrink: 0 }} title={s.source_title || s.source_id}>
                      {s.source_title || s.source_id}
                    </div>
                    <div style={{ flex: 1, height: 18, background: "#f1f5f9", borderRadius: 6, overflow: "hidden", position: "relative" }}>
                      <div style={{ width: `${barPct}%`, height: "100%", background: barColor, borderRadius: 6, transition: "width 300ms ease" }} />
                    </div>
                    <div style={{ width: 32, textAlign: "right", fontSize: "0.78rem", fontWeight: 800, color: textColor, flexShrink: 0 }}>
                      {s.count}
                    </div>
                  </div>
                );
              })}
              {!loading && sourceHotspots.length === 0 && (
                <div style={{ color: "#94a3b8", fontWeight: 600, fontSize: "0.85rem", padding: "0.5rem 0" }}>No content friction data yet.</div>
              )}
              {loading && [1, 2, 3].map((k) => (
                <div key={`hsk-${k}`} style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                  <div style={{ width: 130, height: 12, background: "#e2e8f0", borderRadius: 6 }} />
                  <div style={{ flex: 1, height: 18, background: "#f1f5f9", borderRadius: 6 }} />
                  <div style={{ width: 32, height: 12, background: "#e2e8f0", borderRadius: 6 }} />
                </div>
              ))}
            </div>
            <div style={{ marginTop: "0.6rem", fontSize: "0.72rem", color: "#94a3b8", fontWeight: 600 }}>
              Misconceptions by source content • Last {windowDays}
            </div>
          </div>
        </div>
      </div>

      <style jsx>{`
        @media (max-width: 1200px) {
          main :global(div[style*="grid-template-columns: repeat(4"]) {
            grid-template-columns: repeat(2, minmax(0, 1fr)) !important;
          }
          main :global(div[style*="grid-template-columns: 2fr 1fr"]),
          main :global(div[style*="grid-template-columns: 1fr 1fr"]) {
            grid-template-columns: 1fr !important;
          }
        }
      `}</style>
    </main>
  );
}
