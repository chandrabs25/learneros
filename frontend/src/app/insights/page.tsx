"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import TutorMarkdown from "@/components/TutorMarkdown";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type InsightType = "COMPETENCY" | "PARTIAL_UNDERSTANDING" | "MISCONCEPTION" | "TAUGHT";

interface InsightItem {
  id: string;
  type: InsightType;
  category: string;
  content: string;
  created_at?: string;
  source_id?: string;
  source_title?: string;
  concept_id?: string;
  concept_name?: string;
}

function prettyConcept(ins: InsightItem): string {
  if (ins.concept_name) return ins.concept_name;
  if (ins.concept_id) return ins.concept_id.replace("concept:", "").replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
  return "General Understanding";
}

function prettyType(t: InsightType): string {
  return t.replace(/_/g, " ");
}

const typeColor: Record<InsightType, string> = {
  COMPETENCY: "#10b981",
  PARTIAL_UNDERSTANDING: "#f59e0b",
  MISCONCEPTION: "#ef4444",
  TAUGHT: "#3b82f6",
};

export default function InsightsAnalyticsPage() {
  const router = useRouter();
  const { getIdToken } = useAuth();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [insights, setInsights] = useState<InsightItem[]>([]);
  const [selectedType, setSelectedType] = useState<InsightType | "ALL">("ALL");
  const [explainById, setExplainById] = useState<Record<string, { loading: boolean; text?: string; points?: string[]; error?: string }>>({});
  const [testById, setTestById] = useState<Record<string, {
    loading: boolean;
    question?: string;
    options?: Record<string, string>;
    correct_answer?: string;
    explanation?: string;
    selected?: string;
    evaluating?: boolean;
    feedback?: string;
    done?: boolean;
    error?: string;
  }>>({});

  const loadInsights = async () => {
    setLoading(true);
    setError("");
    try {
      const token = await getIdToken();
      if (!token) {
        setInsights([]);
        setError("Sign in to view your learning analysis.");
        return;
      }
      const res = await fetch(`${API_URL}/api/students/me/insights`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data?.detail || `HTTP ${res.status}`);
      setInsights(Array.isArray(data) ? data : []);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load insights.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadInsights();
  }, [getIdToken]);

  const counts = useMemo(() => {
    const byType: Record<InsightType, number> = {
      COMPETENCY: 0,
      PARTIAL_UNDERSTANDING: 0,
      MISCONCEPTION: 0,
      TAUGHT: 0,
    };
    for (const ins of insights) {
      if (byType[ins.type] !== undefined) byType[ins.type] += 1;
    }
    return byType;
  }, [insights]);

  const conceptGroups = useMemo(() => {
    const filtered = selectedType === "ALL" ? insights : insights.filter((i) => i.type === selectedType);
    const map = new Map<string, { conceptLabel: string; items: InsightItem[] }>();
    for (const ins of filtered) {
      const key = ins.concept_id || "general";
      const label = prettyConcept(ins);
      if (!map.has(key)) map.set(key, { conceptLabel: label, items: [] });
      map.get(key)!.items.push(ins);
    }

    const groups = Array.from(map.entries()).map(([key, v]) => ({ key, ...v }));
    groups.sort((a, b) => {
      const aMis = a.items.filter((i) => i.type === "MISCONCEPTION").length;
      const bMis = b.items.filter((i) => i.type === "MISCONCEPTION").length;
      if (bMis !== aMis) return bMis - aMis;
      return b.items.length - a.items.length;
    });

    return groups;
  }, [insights, selectedType]);

  const runExplain = async (insightId: string) => {
    setExplainById((prev) => ({ ...prev, [insightId]: { loading: true } }));
    try {
      const token = await getIdToken();
      if (!token) throw new Error("Sign in required.");
      const res = await fetch(`${API_URL}/api/students/me/insights/${encodeURIComponent(insightId)}/explain`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data?.detail || `HTTP ${res.status}`);
      setExplainById((prev) => ({
        ...prev,
        [insightId]: {
          loading: false,
          text: data.explanation || "",
          points: Array.isArray(data.key_points) ? data.key_points : [],
        },
      }));
    } catch (e: unknown) {
      setExplainById((prev) => ({
        ...prev,
        [insightId]: { loading: false, error: e instanceof Error ? e.message : "Failed to explain." },
      }));
    }
  };

  const runTest = async (insightId: string) => {
    setTestById((prev) => ({ ...prev, [insightId]: { loading: true } }));
    try {
      const token = await getIdToken();
      if (!token) throw new Error("Sign in required.");
      const res = await fetch(`${API_URL}/api/students/me/insights/${encodeURIComponent(insightId)}/test/mcq`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data?.detail || `HTTP ${res.status}`);
      setTestById((prev) => ({
        ...prev,
        [insightId]: {
          loading: false,
          question: data.question || "",
          options: data.options || {},
          correct_answer: data.correct_answer || "A",
          explanation: data.explanation || "",
          selected: undefined,
          done: false,
        },
      }));
    } catch (e: unknown) {
      setTestById((prev) => ({
        ...prev,
        [insightId]: { loading: false, error: e instanceof Error ? e.message : "Failed to generate test." },
      }));
    }
  };

  const evaluateTest = async (insightId: string) => {
    const t = testById[insightId];
    if (!t?.selected || !t.question || !t.options || !t.correct_answer) return;
    setTestById((prev) => ({ ...prev, [insightId]: { ...prev[insightId], evaluating: true, error: undefined } }));
    try {
      const token = await getIdToken();
      if (!token) throw new Error("Sign in required.");
      const res = await fetch(`${API_URL}/api/students/me/insights/${encodeURIComponent(insightId)}/test/mcq/evaluate`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify({
          question: t.question,
          options: t.options,
          selected: t.selected,
          correct_answer: t.correct_answer,
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data?.detail || `HTTP ${res.status}`);
      setTestById((prev) => ({
        ...prev,
        [insightId]: {
          ...prev[insightId],
          evaluating: false,
          feedback: data.feedback || "",
          done: true,
        },
      }));
      await loadInsights();
    } catch (e: unknown) {
      setTestById((prev) => ({
        ...prev,
        [insightId]: { ...prev[insightId], evaluating: false, error: e instanceof Error ? e.message : "Failed to evaluate." },
      }));
    }
  };

  return (
    <div style={{ minHeight: "100vh", background: "#f6f8f8", padding: "2rem 2.25rem 3rem" }}>
      <div style={{ maxWidth: 1240, margin: "0 auto" }}>
        <div style={{ marginBottom: "2rem" }}>
          <h1 style={{ margin: 0, fontSize: "2.3rem", lineHeight: 1.1, letterSpacing: "-0.03em", fontWeight: 800 }}>Learning Analysis</h1>
          <p style={{ margin: "0.6rem 0 0", color: "#64748b", fontSize: "1.03rem" }}>
            Concept-wise view of your active competencies, partial understandings, and misconceptions.
          </p>
        </div>

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))",
            gap: "1rem",
            marginBottom: "2rem",
          }}
        >
          <SummaryCard
            title="Competencies"
            value={counts.COMPETENCY}
            color="#10b981"
            icon="verified"
            selected={selectedType === "COMPETENCY"}
            onClick={() => setSelectedType((t) => (t === "COMPETENCY" ? "ALL" : "COMPETENCY"))}
          />
          <SummaryCard
            title="Partial Understandings"
            value={counts.PARTIAL_UNDERSTANDING}
            color="#f59e0b"
            icon="pending_actions"
            selected={selectedType === "PARTIAL_UNDERSTANDING"}
            onClick={() => setSelectedType((t) => (t === "PARTIAL_UNDERSTANDING" ? "ALL" : "PARTIAL_UNDERSTANDING"))}
          />
          <SummaryCard
            title="Misconceptions"
            value={counts.MISCONCEPTION}
            color="#ef4444"
            icon="error"
            selected={selectedType === "MISCONCEPTION"}
            onClick={() => setSelectedType((t) => (t === "MISCONCEPTION" ? "ALL" : "MISCONCEPTION"))}
          />
        </div>

        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "1rem", marginBottom: "1rem" }}>
          <h2 style={{ margin: 0, fontSize: "1.65rem", fontWeight: 800, letterSpacing: "-0.02em" }}>Concept-wise Insights</h2>
          <div style={{ fontSize: "0.84rem", color: "#64748b", background: "#eef2ff", borderRadius: 9999, padding: "0.45rem 0.9rem", fontWeight: 600 }}>
            {selectedType === "ALL"
              ? `${insights.length} active insight${insights.length === 1 ? "" : "s"}`
              : `${selectedType.replace(/_/g, " ")} filter`}
          </div>
        </div>

        {loading ? (
          <StateCard text="Loading insights..." />
        ) : error ? (
          <StateCard text={error} />
        ) : conceptGroups.length === 0 ? (
          <StateCard text="No active insights yet. Complete tests or exercises to generate insights." />
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
            {conceptGroups.map((group) => (
              <div
                key={group.key}
                style={{
                  background: "#fff",
                  border: "1px solid #e2e8f0",
                  borderRadius: 16,
                  padding: "1.1rem 1.2rem",
                  boxShadow: "0 6px 22px rgba(15, 23, 42, 0.04)",
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", gap: "1rem", alignItems: "center", marginBottom: "0.7rem" }}>
                  <h3 style={{ margin: 0, fontSize: "1.2rem", fontWeight: 800 }}>{group.conceptLabel}</h3>
                  <span style={{ fontSize: "0.74rem", fontWeight: 700, color: "#64748b", textTransform: "uppercase", letterSpacing: "0.09em" }}>
                    {group.items.length} insight{group.items.length === 1 ? "" : "s"}
                  </span>
                </div>

                <div style={{ display: "grid", gridTemplateColumns: "1fr", gap: "0.65rem" }}>
                  {group.items.map((ins) => (
                    <div
                      key={ins.id}
                      style={{
                        border: "1px solid #e2e8f0",
                        borderLeft: `4px solid ${typeColor[ins.type] || "#94a3b8"}`,
                        borderRadius: 12,
                        padding: "0.8rem 0.9rem",
                        background: "#f8fafc",
                      }}
                    >
                      <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", flexWrap: "wrap", marginBottom: "0.35rem" }}>
                        <span style={{ fontSize: "0.7rem", fontWeight: 800, letterSpacing: "0.08em", textTransform: "uppercase", color: typeColor[ins.type] || "#64748b" }}>
                          {prettyType(ins.type)}
                        </span>
                        <span style={{ fontSize: "0.64rem", fontWeight: 700, color: "#64748b", textTransform: "uppercase", letterSpacing: "0.08em", background: "#e2e8f0", borderRadius: 9999, padding: "0.15rem 0.45rem" }}>
                          {ins.category}
                        </span>
                        {ins.source_title && (
                          <span style={{ fontSize: "0.64rem", color: "#64748b", marginLeft: "auto" }}>{ins.source_title}</span>
                        )}
                      </div>
                      <p style={{ margin: 0, color: "#0f172a", fontSize: "0.96rem", lineHeight: 1.55 }}>{ins.content}</p>

                      {(ins.type === "PARTIAL_UNDERSTANDING" || ins.type === "MISCONCEPTION") && (
                        <div style={{ marginTop: "0.75rem", display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
                          <button
                            onClick={() => runExplain(ins.id)}
                            style={{
                              display: "inline-flex",
                              alignItems: "center",
                              gap: "0.3rem",
                              padding: "0.45rem 0.8rem",
                              borderRadius: 10,
                              border: "none",
                              background: "#13ecda",
                              color: "#042b28",
                              fontWeight: 800,
                              cursor: "pointer",
                              fontFamily: "var(--font-display)",
                              fontSize: "0.8rem",
                            }}
                          >
                            <span className="material-symbols-outlined" style={{ fontSize: 16 }}>bolt</span>
                            Explain
                          </button>
                          <button
                            onClick={() => runTest(ins.id)}
                            style={{
                              display: "inline-flex",
                              alignItems: "center",
                              gap: "0.3rem",
                              padding: "0.45rem 0.8rem",
                              borderRadius: 10,
                              border: "none",
                              background: "#3498db",
                              color: "white",
                              fontWeight: 800,
                              cursor: "pointer",
                              fontFamily: "var(--font-display)",
                              fontSize: "0.8rem",
                            }}
                          >
                            <span className="material-symbols-outlined" style={{ fontSize: 16 }}>quiz</span>
                            Test
                          </button>
                        </div>
                      )}

                      {explainById[ins.id] && (
                        <div style={{ marginTop: "0.65rem", borderRadius: 10, border: "1px solid #bae6fd", background: "#ecfeff", padding: "0.65rem 0.75rem" }}>
                          {explainById[ins.id].loading ? (
                            <p style={{ margin: 0, fontSize: "0.85rem", color: "#0f172a" }}>Generating explanation...</p>
                          ) : explainById[ins.id].error ? (
                            <p style={{ margin: 0, fontSize: "0.85rem", color: "#b91c1c" }}>{explainById[ins.id].error}</p>
                          ) : (
                            <>
                              <TutorMarkdown text={explainById[ins.id].text || ""} compact />
                              {!!explainById[ins.id].points?.length && (
                                <ul style={{ margin: "0.45rem 0 0", paddingLeft: "1rem" }}>
                                  {explainById[ins.id].points!.map((p, i) => (
                                    <li key={i} style={{ fontSize: "0.82rem", color: "#334155", marginBottom: "0.25rem" }}>
                                      <TutorMarkdown text={p} compact />
                                    </li>
                                  ))}
                                </ul>
                              )}
                            </>
                          )}
                        </div>
                      )}

                      {testById[ins.id] && (
                        <div style={{ marginTop: "0.65rem", borderRadius: 10, border: "1px solid #bfdbfe", background: "#eff6ff", padding: "0.7rem 0.75rem" }}>
                          {testById[ins.id].loading ? (
                            <p style={{ margin: 0, fontSize: "0.85rem", color: "#0f172a" }}>Generating MCQ...</p>
                          ) : testById[ins.id].error ? (
                            <p style={{ margin: 0, fontSize: "0.85rem", color: "#b91c1c" }}>{testById[ins.id].error}</p>
                          ) : (
                            <>
                              <TutorMarkdown text={testById[ins.id].question || ""} compact />
                              <div style={{ display: "grid", gap: "0.35rem", marginTop: "0.5rem" }}>
                                {Object.entries(testById[ins.id].options || {}).map(([k, v]) => (
                                  <button
                                    key={k}
                                    onClick={() => setTestById((prev) => ({ ...prev, [ins.id]: { ...prev[ins.id], selected: k } }))}
                                    style={{
                                      textAlign: "left",
                                      borderRadius: 8,
                                      border: `1px solid ${(testById[ins.id].selected === k) ? "#2563eb" : "#cbd5e1"}`,
                                      background: (testById[ins.id].selected === k) ? "#dbeafe" : "white",
                                      padding: "0.45rem 0.55rem",
                                      cursor: "pointer",
                                      fontSize: "0.84rem",
                                      color: "#0f172a",
                                      fontFamily: "var(--font-body)",
                                    }}
                                  >
                                    <span style={{ display: "inline-flex", gap: "0.35rem", alignItems: "flex-start" }}>
                                      <strong style={{ marginTop: 2 }}>{k}.</strong>
                                      <span style={{ flex: 1 }}>
                                        <TutorMarkdown text={String(v)} compact />
                                      </span>
                                    </span>
                                  </button>
                                ))}
                              </div>
                              <div style={{ marginTop: "0.55rem", display: "flex", gap: "0.5rem", alignItems: "center", flexWrap: "wrap" }}>
                                <button
                                  onClick={() => evaluateTest(ins.id)}
                                  disabled={!testById[ins.id].selected || !!testById[ins.id].evaluating}
                                  style={{
                                    border: "none",
                                    borderRadius: 8,
                                    background: "#1d4ed8",
                                    color: "white",
                                    fontSize: "0.8rem",
                                    fontWeight: 800,
                                    padding: "0.42rem 0.75rem",
                                    cursor: (!testById[ins.id].selected || !!testById[ins.id].evaluating) ? "not-allowed" : "pointer",
                                    opacity: (!testById[ins.id].selected || !!testById[ins.id].evaluating) ? 0.6 : 1,
                                  }}
                                >
                                  {testById[ins.id].evaluating ? "Checking..." : "Submit Test"}
                                </button>
                                {testById[ins.id].done && (
                                  <span style={{ fontSize: "0.78rem", color: "#065f46", fontWeight: 700 }}>
                                    Reconciled and saved.
                                  </span>
                                )}
                              </div>
                              {!!testById[ins.id].feedback && (
                                <div style={{ marginTop: "0.45rem", fontSize: "0.82rem", color: "#1e3a8a" }}>
                                  <TutorMarkdown text={testById[ins.id].feedback || ""} compact />
                                </div>
                              )}
                            </>
                          )}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}

        <div style={{ marginTop: "2rem", padding: "2rem 1.5rem", background: "linear-gradient(135deg, #0b1739 0%, #0f2540 100%)", color: "#e2e8f0", borderRadius: 22, textAlign: "center" }}>
          <span className="material-symbols-outlined" style={{ fontSize: 44, color: "#13ecda" }}>psychology</span>
          <h3 style={{ margin: "0.45rem 0 0", fontSize: "2rem", fontWeight: 800, color: "#fff" }}>Master Your Knowledge Gaps</h3>
          <p style={{ margin: "0.55rem auto 0", maxWidth: 700, color: "#94a3b8", fontSize: "1.02rem" }}>
            Focus on misconception-heavy concepts first. A short, targeted revision session can quickly move these into competencies.
          </p>
          <button
            onClick={() => router.push("/")}
            style={{ marginTop: "1rem", background: "#13ecda", color: "#0f172a", border: "none", borderRadius: 12, padding: "0.8rem 1.5rem", fontWeight: 800, cursor: "pointer", fontFamily: "var(--font-display)" }}
          >
            Start Recovery Path
          </button>
        </div>
      </div>
    </div>
  );
}

function StateCard({ text }: { text: string }) {
  return (
    <div style={{ background: "#fff", border: "1px solid #e2e8f0", borderRadius: 14, padding: "1.1rem 1rem", color: "#64748b", fontWeight: 600 }}>
      {text}
    </div>
  );
}

function SummaryCard({
  title,
  value,
  color,
  icon,
  selected = false,
  onClick,
}: {
  title: string;
  value: number;
  color: string;
  icon: string;
  selected?: boolean;
  onClick?: () => void;
}) {
  return (
    <div
      onClick={onClick}
      style={{
        background: "#fff",
        border: selected ? `2px solid ${color}` : "1px solid #e2e8f0",
        borderRadius: 16,
        padding: "1rem 1rem 0.9rem",
        boxShadow: selected ? `0 8px 24px ${color}33` : "0 6px 22px rgba(15, 23, 42, 0.04)",
        cursor: onClick ? "pointer" : "default",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "0.7rem" }}>
        <span className="material-symbols-outlined" style={{ color, fontSize: 26 }}>{icon}</span>
      </div>
      <p style={{ margin: 0, color: "#64748b", fontSize: "0.78rem", letterSpacing: "0.13em", textTransform: "uppercase", fontWeight: 700 }}>{title}</p>
      <p style={{ margin: "0.2rem 0 0", fontSize: "2.55rem", lineHeight: 1, fontWeight: 900 }}>{value}</p>
    </div>
  );
}
