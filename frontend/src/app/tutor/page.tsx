"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import TutorMarkdown from "@/components/TutorMarkdown";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface InsightItem {
  id: string;
  type: string;
  category: string;
  content: string;
  concept_id?: string;
  concept_name?: string;
  source_id?: string;
  source_title?: string;
  similarity?: number;
}

interface ChatMessage {
  role: "user" | "assistant";
  text: string;
}

interface TutorHistoryMessage {
  role: "user" | "assistant";
  content: string;
}

interface MatchedConcept {
  key: string;
  concept: string;
  conceptId?: string;
  count: number;
  topType?: string;
}

interface LineageNode {
  id: string;
  type: "concept" | "grade" | "subject" | "chapter";
  label: string;
  meta?: Record<string, string>;
}

interface LineageEdge {
  source: string;
  target: string;
  type: string;
}

interface LineagePayload {
  concept: { id: string; name: string };
  nodes: LineageNode[];
  edges: LineageEdge[];
  meta: { chapter_total: number; chapter_returned: number; limit: number; truncated: boolean };
}

type Point = { x: number; y: number };

const typeColor: Record<LineageNode["type"], string> = {
  concept: "#f97316",
  grade: "#0ea5e9",
  subject: "#8b5cf6",
  chapter: "#10b981",
};

function trimLabel(text: string, max = 38): string {
  return text.length > max ? `${text.slice(0, max - 1)}…` : text;
}

function toSubjectSlug(subjectName: string): string {
  return subjectName
    .trim()
    .toLowerCase()
    .replace(/&/g, "and")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .replace(/--+/g, "-");
}

function buildLineageLayout(nodes: LineageNode[]): {
  points: Record<string, Point>;
  width: number;
  height: number;
} {
  const levelOrder: LineageNode["type"][] = ["concept", "grade", "subject", "chapter"];
  const xByLevel: Record<LineageNode["type"], number> = {
    concept: 80,
    grade: 260,
    subject: 460,
    chapter: 700,
  };
  const nodeH = 44;
  const startY = 50;
  const gapY = 68;
  const points: Record<string, Point> = {};
  let maxCount = 1;

  for (const level of levelOrder) {
    const levelNodes = nodes
      .filter((n) => n.type === level)
      .sort((a, b) => a.label.localeCompare(b.label, undefined, { sensitivity: "base" }));
    maxCount = Math.max(maxCount, levelNodes.length);
    levelNodes.forEach((node, idx) => {
      points[node.id] = { x: xByLevel[level], y: startY + idx * gapY + nodeH / 2 };
    });
  }

  const height = Math.max(220, startY + maxCount * gapY + 24);
  const width = 860;
  return { points, width, height };
}

export default function TutorPage() {
  const { getIdToken } = useAuth();
  const router = useRouter();
  const lineageAbortRef = useRef<AbortController | null>(null);

  const [sessionId, setSessionId] = useState("");
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role: "assistant",
      text: "How can I assist your learning today? I can explain any topic and personalize based on your active insights when relevant.",
    },
  ]);

  const [matchedInsights, setMatchedInsights] = useState<InsightItem[]>([]);
  const [historyLoaded, setHistoryLoaded] = useState(false);

  const [lineageOpen, setLineageOpen] = useState(false);
  const [selectedConcept, setSelectedConcept] = useState<MatchedConcept | null>(null);
  const [lineageLoading, setLineageLoading] = useState(false);
  const [lineageError, setLineageError] = useState("");
  const [lineageData, setLineageData] = useState<LineagePayload | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const token = await getIdToken();
        if (!token) {
          if (!cancelled) setHistoryLoaded(true);
          return;
        }
        const res = await fetch(`${API_URL}/api/tutor/session/latest`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data?.detail || `HTTP ${res.status}`);
        const history: TutorHistoryMessage[] = Array.isArray(data?.messages) ? data.messages : [];
        if (!cancelled && data?.session_id && history.length > 0) {
          setSessionId(data.session_id);
          setMessages(history.map((m) => ({ role: m.role, text: m.content })));
        }
      } catch {
        // Keep starter message when history can't be loaded.
      } finally {
        if (!cancelled) setHistoryLoaded(true);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [getIdToken]);

  useEffect(() => {
    return () => {
      lineageAbortRef.current?.abort();
    };
  }, []);

  const matchedConcepts = useMemo<MatchedConcept[]>(() => {
    const map = new Map<string, MatchedConcept>();
    for (const ins of matchedInsights) {
      const key = ins.concept_id || ins.concept_name || "general";
      const concept = ins.concept_name || (ins.concept_id ? ins.concept_id.replace("concept:", "").replace(/_/g, " ") : "General");
      if (!map.has(key)) {
        map.set(key, { key, concept, conceptId: ins.concept_id, count: 0, topType: ins.type });
      }
      const row = map.get(key)!;
      row.count += 1;
      row.topType = row.topType || ins.type;
      if (!row.conceptId && ins.concept_id) row.conceptId = ins.concept_id;
    }
    return Array.from(map.values()).sort((a, b) => b.count - a.count);
  }, [matchedInsights]);

  useEffect(() => {
    if (!selectedConcept?.conceptId) return;
    const stillExists = matchedConcepts.some((c) => c.conceptId === selectedConcept.conceptId);
    if (!stillExists) {
      setLineageOpen(false);
      setSelectedConcept(null);
      setLineageData(null);
      setLineageError("");
      setLineageLoading(false);
    }
  }, [matchedConcepts, selectedConcept]);

  const sendMessage = async (raw: string) => {
    const message = raw.trim();
    if (!message || sending) return;
    setInput("");
    setMessages((prev) => [...prev, { role: "user", text: message }]);
    setSending(true);
    try {
      const token = await getIdToken();
      const headers: Record<string, string> = { "Content-Type": "application/json" };
      if (token) headers.Authorization = `Bearer ${token}`;
      const res = await fetch(`${API_URL}/api/tutor/chat`, {
        method: "POST",
        headers,
        body: JSON.stringify({ message, session_id: sessionId || undefined }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data?.detail || `HTTP ${res.status}`);
      if (!sessionId && data?.session_id) setSessionId(data.session_id);
      const matched = Array.isArray(data?.matched_insights) ? data.matched_insights : [];
      setMatchedInsights(matched);
      setMessages((prev) => [...prev, { role: "assistant", text: data?.response || "I could not generate a response." }]);
    } catch (e: unknown) {
      setMessages((prev) => [...prev, { role: "assistant", text: e instanceof Error ? e.message : "Failed to contact LearnerOS Tutor." }]);
    } finally {
      setSending(false);
    }
  };

  const loadLineage = async (concept: MatchedConcept) => {
    if (!concept.conceptId) return;
    lineageAbortRef.current?.abort();
    const controller = new AbortController();
    lineageAbortRef.current = controller;

    setSelectedConcept(concept);
    setLineageOpen(true);
    setLineageLoading(true);
    setLineageError("");

    try {
      const res = await fetch(
        `${API_URL}/api/concepts/${encodeURIComponent(concept.conceptId)}/lineage?chapter_limit=60&v=2`,
        { signal: controller.signal },
      );
      const data = (await res.json()) as LineagePayload | { detail?: string };
      if (!res.ok) {
        throw new Error((data as { detail?: string })?.detail || `HTTP ${res.status}`);
      }
      setLineageData(data as LineagePayload);
    } catch (e: unknown) {
      if (e instanceof Error && e.name === "AbortError") return;
      setLineageData(null);
      setLineageError(e instanceof Error ? e.message : "Failed to load concept lineage.");
    } finally {
      setLineageLoading(false);
    }
  };

  const newExploration = () => {
    setSessionId("");
    setMatchedInsights([]);
    setLineageOpen(false);
    setSelectedConcept(null);
    setLineageData(null);
    setLineageError("");
    setMessages([
      {
        role: "assistant",
        text: "New exploration started. What topic do you want to learn now?",
      },
    ]);
  };

  const lineageNodes = lineageData?.nodes ?? [];
  const lineageEdges = lineageData?.edges ?? [];
  const layout = useMemo(() => buildLineageLayout(lineageNodes), [lineageNodes]);
  const nodeById = useMemo(() => {
    const map = new Map<string, LineageNode>();
    lineageNodes.forEach((n) => map.set(n.id, n));
    return map;
  }, [lineageNodes]);

  const handleChapterClick = (node: LineageNode) => {
    if (node.type !== "chapter") return;
    const grade = node.meta?.grade;
    const chapterNumber = node.meta?.chapter_number;
    const subjectSlug = node.meta?.subject_slug || toSubjectSlug(node.meta?.subject_name || "");
    if (!grade || !chapterNumber || !subjectSlug) return;
    setLineageOpen(false);
    router.push(`/${encodeURIComponent(grade)}/${encodeURIComponent(subjectSlug)}/${encodeURIComponent(chapterNumber)}`);
  };

  return (
    <div className="tutor-layout" style={{ height: "calc(100vh - 64px)", background: "#f8f6f5", overflow: "hidden", position: "relative" }}>
      <aside className="tutor-left" style={{ borderRight: "1px solid #e2e8f0", background: "#fff", padding: "1rem", display: "flex", flexDirection: "column", gap: "1rem", minHeight: 0 }}>
        <div style={{ fontSize: "0.68rem", letterSpacing: "0.12em", fontWeight: 800, textTransform: "uppercase", color: "#94a3b8" }}>Matched Insights</div>
        <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem", overflowY: "auto", minHeight: 0 }}>
          {matchedInsights.length === 0 ? (
            <div style={{ fontSize: "0.85rem", color: "#64748b" }}>No query-matched insights yet. Ask a question to retrieve relevant active insights.</div>
          ) : (
            matchedInsights.map((ins) => (
              <div
                key={ins.id}
                style={{
                  border: "1px solid #fb923c",
                  background: "#fff7ed",
                  borderRadius: 10,
                  padding: "0.6rem",
                }}
              >
                <div style={{ display: "flex", gap: "0.35rem", alignItems: "center", marginBottom: "0.25rem" }}>
                  <span style={{ fontSize: "0.62rem", fontWeight: 800, textTransform: "uppercase", color: "#c2410c" }}>{ins.type.replace(/_/g, " ")}</span>
                  <span style={{ fontSize: "0.62rem", color: "#94a3b8" }}>{ins.category}</span>
                </div>
                <div style={{ fontSize: "0.8rem", fontWeight: 700, color: "#0f172a", marginBottom: "0.2rem" }}>{ins.concept_name || ins.concept_id || "General"}</div>
                <div style={{ fontSize: "0.76rem", color: "#334155", lineHeight: 1.4 }}>{ins.content}</div>
              </div>
            ))
          )}
        </div>
        <button
          onClick={newExploration}
          style={{ marginTop: "auto", border: "2px dashed #cbd5e1", borderRadius: 10, background: "transparent", padding: "0.7rem", fontWeight: 800, fontSize: "0.85rem", cursor: "pointer", fontFamily: "var(--font-display)" }}
        >
          + New Exploration
        </button>
      </aside>

      <section className="tutor-center" style={{ display: "flex", flexDirection: "column", minWidth: 0, minHeight: 0, overflow: "hidden" }}>
        <div style={{ flex: 1, overflowY: "auto", padding: "1.2rem 1.5rem", minHeight: 0 }}>
          <div style={{ maxWidth: 900, margin: "0 auto", display: "flex", flexDirection: "column", gap: "0.8rem" }}>
            {!historyLoaded ? (
              <div style={{ color: "#64748b", fontSize: "0.9rem" }}>Loading conversation...</div>
            ) : messages.map((m, i) => (
              <div
                key={i}
                style={{
                  alignSelf: m.role === "user" ? "flex-end" : "flex-start",
                  maxWidth: "90%",
                  borderRadius: 18,
                  background: m.role === "user" ? "#0f172a" : "#fff",
                  color: m.role === "user" ? "#fff" : "#0f172a",
                  border: m.role === "user" ? "none" : "1px solid #e2e8f0",
                  boxShadow: m.role === "user" ? "0 10px 24px rgba(2, 6, 23, 0.25)" : "0 6px 16px rgba(15, 23, 42, 0.04)",
                  padding: "0.9rem 1rem",
                  fontSize: "1rem",
                  lineHeight: 1.6,
                  overflowWrap: "anywhere",
                }}
              >
                <TutorMarkdown text={m.text || ""} isUser={m.role === "user"} />
              </div>
            ))}
          </div>
        </div>

        <div style={{ borderTop: "1px solid #e2e8f0", background: "#f8f6f5", padding: "0.85rem 1.25rem 1rem", flexShrink: 0 }}>
          <div style={{ maxWidth: 900, margin: "0 auto" }}>
            <div style={{ display: "flex", gap: "0.5rem", background: "#fff", border: "1px solid #e2e8f0", borderRadius: 20, padding: "0.45rem" }}>
              <input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    e.preventDefault();
                    sendMessage(input);
                  }
                }}
                placeholder="Ask me anything about any subject..."
                style={{ flex: 1, border: "none", outline: "none", fontSize: "1rem", padding: "0.6rem 0.8rem", background: "transparent", fontFamily: "var(--font-body)" }}
              />
              <button
                onClick={() => sendMessage(input)}
                disabled={sending || !input.trim()}
                style={{ border: "none", borderRadius: 14, background: "#f45c25", color: "#fff", width: 48, height: 48, cursor: sending || !input.trim() ? "not-allowed" : "pointer", opacity: sending || !input.trim() ? 0.6 : 1 }}
              >
                <span className="material-symbols-outlined">arrow_upward</span>
              </button>
            </div>
          </div>
        </div>
      </section>

      <aside className="tutor-right" style={{ borderLeft: "1px solid #e2e8f0", background: "#fff", padding: "1rem", display: "flex", flexDirection: "column", gap: "0.8rem", minHeight: 0 }}>
        <div style={{ fontSize: "0.68rem", letterSpacing: "0.12em", fontWeight: 800, textTransform: "uppercase", color: "#94a3b8" }}>Matched Concepts</div>
        <div style={{ display: "flex", flexDirection: "column", gap: "0.55rem", overflowY: "auto", minHeight: 0 }}>
          {matchedConcepts.length === 0 ? (
            <div style={{ fontSize: "0.85rem", color: "#64748b" }}>No concept matches yet. Ask a question to start.</div>
          ) : (
            matchedConcepts.map((c, i) => (
              <div key={`${c.key}-${i}`} style={{ border: "1px solid #e2e8f0", borderRadius: 10, padding: "0.65rem", background: "#f8fafc" }}>
                <div style={{ fontSize: "0.95rem", fontWeight: 800, marginBottom: "0.25rem" }}>{c.concept}</div>
                <div style={{ display: "flex", gap: "0.4rem", alignItems: "center", marginBottom: "0.45rem" }}>
                  <span style={{ fontSize: "0.64rem", textTransform: "uppercase", color: "#64748b", fontWeight: 800 }}>{c.topType?.replace(/_/g, " ") || "Related"}</span>
                  <span style={{ fontSize: "0.64rem", color: "#94a3b8" }}>{c.count} match{c.count === 1 ? "" : "es"}</span>
                </div>
                <button
                  type="button"
                  onClick={() => loadLineage(c)}
                  disabled={!c.conceptId}
                  title={!c.conceptId ? "Graph unavailable for this concept" : "View concept lineage graph"}
                  style={{
                    width: "100%",
                    borderRadius: 8,
                    border: "1px solid #cbd5e1",
                    background: c.conceptId ? "#ffffff" : "#f1f5f9",
                    color: c.conceptId ? "#0f172a" : "#94a3b8",
                    fontSize: "0.74rem",
                    fontWeight: 700,
                    padding: "0.35rem 0.5rem",
                    cursor: c.conceptId ? "pointer" : "not-allowed",
                  }}
                >
                  View Graph
                </button>
              </div>
            ))
          )}
        </div>
      </aside>

      {lineageOpen && (
        <aside
          style={{
            position: "absolute",
            right: 0,
            top: 0,
            bottom: 0,
            width: "min(68vw, 920px)",
            maxWidth: "100%",
            background: "#ffffff",
            borderLeft: "1px solid #e2e8f0",
            boxShadow: "-16px 0 32px rgba(2, 6, 23, 0.14)",
            zIndex: 40,
            display: "flex",
            flexDirection: "column",
          }}
        >
          <div style={{ padding: "0.85rem 1rem", borderBottom: "1px solid #e2e8f0", display: "flex", justifyContent: "space-between", alignItems: "center", gap: "0.8rem" }}>
            <div style={{ minWidth: 0 }}>
              <div style={{ fontSize: "0.68rem", letterSpacing: "0.12em", fontWeight: 800, textTransform: "uppercase", color: "#94a3b8" }}>
                Concept Lineage
              </div>
              <div style={{ fontSize: "1.02rem", fontWeight: 800, color: "#0f172a", whiteSpace: "nowrap", textOverflow: "ellipsis", overflow: "hidden" }}>
                {selectedConcept?.concept || "Concept"}
              </div>
            </div>
            <button
              type="button"
              onClick={() => setLineageOpen(false)}
              style={{ border: "1px solid #cbd5e1", borderRadius: 8, width: 34, height: 34, background: "#fff", cursor: "pointer" }}
            >
              <span className="material-symbols-outlined" style={{ fontSize: 18 }}>close</span>
            </button>
          </div>

          <div style={{ padding: "0.8rem 1rem", borderBottom: "1px solid #f1f5f9", display: "flex", gap: "0.6rem", flexWrap: "wrap" }}>
            {(["concept", "grade", "subject", "chapter"] as const).map((t) => (
              <span key={t} style={{ display: "inline-flex", alignItems: "center", gap: 6, fontSize: "0.72rem", fontWeight: 700, color: "#334155" }}>
                <span style={{ width: 8, height: 8, borderRadius: 999, background: typeColor[t], display: "inline-block" }} />
                {t.toUpperCase()}
              </span>
            ))}
          </div>

          <div style={{ flex: 1, minHeight: 0, overflow: "auto", padding: "0.75rem 0.9rem 1rem" }}>
            {lineageLoading ? (
              <div style={{ color: "#64748b", fontSize: "0.9rem" }}>Loading lineage graph...</div>
            ) : lineageError ? (
              <div style={{ border: "1px solid #fecaca", background: "#fef2f2", color: "#b91c1c", borderRadius: 10, padding: "0.8rem", fontSize: "0.86rem" }}>
                {lineageError}
                {selectedConcept?.conceptId && (
                  <button
                    type="button"
                    onClick={() => loadLineage(selectedConcept)}
                    style={{ marginLeft: 10, border: "1px solid #ef4444", color: "#b91c1c", background: "#fff", borderRadius: 8, padding: "0.25rem 0.5rem", cursor: "pointer", fontWeight: 700 }}
                  >
                    Retry
                  </button>
                )}
              </div>
            ) : !lineageData || lineageData.nodes.length <= 1 ? (
              <div style={{ border: "1px solid #e2e8f0", background: "#f8fafc", borderRadius: 10, padding: "0.9rem", color: "#475569", fontSize: "0.86rem" }}>
                No chapter connections found for this concept yet.
              </div>
            ) : (
              <>
                {lineageData.meta.truncated && (
                  <div style={{ marginBottom: "0.6rem", border: "1px solid #fde68a", background: "#fffbeb", borderRadius: 8, padding: "0.55rem 0.7rem", fontSize: "0.78rem", color: "#92400e" }}>
                    Showing {lineageData.meta.chapter_returned} of {lineageData.meta.chapter_total} chapters (cap: {lineageData.meta.limit}).
                  </div>
                )}
                <div style={{ border: "1px solid #e2e8f0", borderRadius: 12, background: "#f8fafc", overflow: "auto" }}>
                  <svg width={layout.width} height={layout.height}>
                    {lineageEdges.map((edge, i) => {
                      const from = layout.points[edge.source];
                      const to = layout.points[edge.target];
                      if (!from || !to) return null;
                      return (
                        <line
                          key={`${edge.source}-${edge.target}-${i}`}
                          x1={from.x + 62}
                          y1={from.y}
                          x2={to.x - 62}
                          y2={to.y}
                          stroke="#cbd5e1"
                          strokeWidth="1.4"
                        />
                      );
                    })}
                    {lineageNodes.map((node) => {
                      const pt = layout.points[node.id];
                      if (!pt) return null;
                      const fill = node.type === "chapter" ? "#f1f5f9" : "#ffffff";
                      const stroke = typeColor[node.type];
                      return (
                        <g key={node.id}>
                          <rect
                            x={pt.x - 62}
                            y={pt.y - 20}
                            width={124}
                            height={40}
                            rx={10}
                            fill={fill}
                            stroke={stroke}
                            strokeWidth={1.4}
                            style={node.type === "chapter" ? { cursor: "pointer" } : undefined}
                            onClick={() => handleChapterClick(node)}
                          />
                          <text
                            x={pt.x}
                            y={pt.y + 4}
                            textAnchor="middle"
                            fill="#0f172a"
                            fontSize={11.5}
                            fontWeight={700}
                            style={node.type === "chapter" ? { cursor: "pointer" } : undefined}
                            onClick={() => handleChapterClick(node)}
                          >
                            {trimLabel(node.label, node.type === "chapter" ? 20 : 18)}
                          </text>
                        </g>
                      );
                    })}
                  </svg>
                </div>
                <div style={{ marginTop: "0.55rem", color: "#64748b", fontSize: "0.75rem" }}>
                  Tip: click any chapter node to open that chapter.
                </div>
              </>
            )}
          </div>
        </aside>
      )}

      <style jsx>{`
        .tutor-layout {
          display: grid;
          grid-template-columns: 280px 1fr 300px;
        }
        @media (max-width: 1200px) {
          .tutor-layout {
            grid-template-columns: 250px 1fr 260px;
          }
        }
        @media (max-width: 960px) {
          .tutor-layout {
            grid-template-columns: 1fr;
          }
          .tutor-left,
          .tutor-right {
            display: none !important;
          }
          .tutor-center {
            min-height: calc(100vh - 64px);
          }
        }
      `}</style>
    </div>
  );
}
