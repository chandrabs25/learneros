"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import Graph from "graphology";
import forceAtlas2 from "graphology-layout-forceatlas2";
import Sigma from "sigma";
import TutorMarkdown from "@/components/TutorMarkdown";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface GraphNodeData {
  id: string;
  label: string;
  type: "chapter" | "concept";
  grade?: number;
  subject?: string;
  number?: number;
  insight_type?: "COMPETENCY" | "PARTIAL_UNDERSTANDING" | "MISCONCEPTION" | null;
}

interface GraphEdgeData {
  source: string;
  target: string;
}

interface InsightsGraphProps {
  token: string | null;
  onConceptClick?: (conceptId: string) => void;
}

interface InsightItem {
  id: string;
  type: string;
  category: string;
  content: string;
  created_at?: string;
  source_id?: string;
  source_title?: string;
  concept_id?: string;
  concept_name?: string;
  is_active?: boolean;
}

interface ExplainState {
  loading: boolean;
  text?: string;
  points?: string[];
  error?: string;
}

interface TestState {
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
}

const INSIGHT_COLORS: Record<string, string> = {
  COMPETENCY: "#10b981",
  PARTIAL_UNDERSTANDING: "#f59e0b",
  MISCONCEPTION: "#ef4444",
};

const TYPE_ICON: Record<string, string> = {
  COMPETENCY: "check_circle",
  PARTIAL_UNDERSTANDING: "help",
  MISCONCEPTION: "error",
  TAUGHT: "school",
};

export default function InsightsGraph({ token, onConceptClick }: InsightsGraphProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const sigmaRef = useRef<Sigma | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [hoveredNode, setHoveredNode] = useState<string | null>(null);
  const [stats, setStats] = useState({ chapters: 0, concepts: 0, withInsights: 0 });

  // Panel state
  const [panelOpen, setPanelOpen] = useState(false);
  const [panelNode, setPanelNode] = useState<{ id: string; label: string; type: string } | null>(null);
  const [panelInsights, setPanelInsights] = useState<InsightItem[]>([]);
  const [panelLoading, setPanelLoading] = useState(false);
  const [panelError, setPanelError] = useState("");
  const [explainById, setExplainById] = useState<Record<string, ExplainState>>({});
  const [testById, setTestById] = useState<Record<string, TestState>>({});

  // ── Fetch insights for clicked node ──
  const fetchInsightsForNode = useCallback(async (nodeId: string, nodeType: string) => {
    if (!token) {
      setPanelError("Sign in to view insights.");
      setPanelLoading(false);
      return;
    }
    setPanelLoading(true);
    setPanelError("");
    setPanelInsights([]);
    setExplainById({});
    setTestById({});

    try {
      const headers: Record<string, string> = { Authorization: `Bearer ${token}` };
      let url: string;

      if (nodeType === "concept") {
        url = `${API_URL}/api/students/me/insights/concept/${encodeURIComponent(nodeId)}`;
      } else {
        url = `${API_URL}/api/students/me/insights?chapter_id=${encodeURIComponent(nodeId)}`;
      }

      const res = await fetch(url, { headers });
      const data = await res.json();
      if (!res.ok) throw new Error(data?.detail || `HTTP ${res.status}`);

      const insights: InsightItem[] = (Array.isArray(data) ? data : [])
        .filter((ins: InsightItem) => ins.is_active !== false);
      setPanelInsights(insights);
    } catch (e: unknown) {
      setPanelError(e instanceof Error ? e.message : "Failed to load insights.");
    } finally {
      setPanelLoading(false);
    }
  }, [token]);

  // ── Explain / Test / Evaluate actions ──
  const runExplain = useCallback(async (insightId: string) => {
    if (!token) return;
    setExplainById((prev) => ({ ...prev, [insightId]: { loading: true } }));
    try {
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
        [insightId]: { loading: false, error: e instanceof Error ? e.message : "Failed." },
      }));
    }
  }, [token]);

  const runTest = useCallback(async (insightId: string) => {
    if (!token) return;
    setTestById((prev) => ({ ...prev, [insightId]: { loading: true } }));
    try {
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
        },
      }));
    } catch (e: unknown) {
      setTestById((prev) => ({
        ...prev,
        [insightId]: { loading: false, error: e instanceof Error ? e.message : "Failed." },
      }));
    }
  }, [token]);

  const evaluateTest = useCallback(async (insightId: string) => {
    if (!token) return;
    const t = testById[insightId];
    if (!t?.selected || !t.question || !t.options || !t.correct_answer) return;
    setTestById((prev) => ({ ...prev, [insightId]: { ...prev[insightId], evaluating: true, error: undefined } }));
    try {
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
        [insightId]: { ...prev[insightId], evaluating: false, feedback: data.feedback || "", done: true },
      }));
      // Reload insights after evaluation
      if (panelNode) {
        fetchInsightsForNode(panelNode.id, panelNode.type);
      }
    } catch (e: unknown) {
      setTestById((prev) => ({
        ...prev,
        [insightId]: { ...prev[insightId], evaluating: false, error: e instanceof Error ? e.message : "Failed." },
      }));
    }
  }, [token, testById, panelNode, fetchInsightsForNode]);

  // ── Handle node click ──
  const handleNodeClick = useCallback((nodeId: string, nodeLabel: string, nodeType: string) => {
    setPanelNode({ id: nodeId, label: nodeLabel, type: nodeType });
    setPanelOpen(true);
    fetchInsightsForNode(nodeId, nodeType);

    // Also fire the external callback for concept scroll
    if (nodeType === "concept" && onConceptClick) {
      onConceptClick(nodeId);
    }
  }, [fetchInsightsForNode, onConceptClick]);

  // ── Build graph ──
  const buildGraph = useCallback(
    async (container: HTMLDivElement) => {
      setLoading(true);
      setError("");

      try {
        const headers: Record<string, string> = {};
        if (token) headers["Authorization"] = `Bearer ${token}`;

        const res = await fetch(`${API_URL}/api/insights/graph`, { headers });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);

        const data = await res.json();
        const nodes: GraphNodeData[] = data.nodes || [];
        const edges: GraphEdgeData[] = data.edges || [];

        if (nodes.length === 0) {
          setError("No curriculum data available.");
          setLoading(false);
          return;
        }

        const chapterCount = nodes.filter((n) => n.type === "chapter").length;
        const conceptCount = nodes.filter((n) => n.type === "concept").length;
        const withInsights = nodes.filter((n) => n.type === "concept" && n.insight_type).length;
        setStats({ chapters: chapterCount, concepts: conceptCount, withInsights });

        const graph = new Graph();

        for (const node of nodes) {
          const isChapter = node.type === "chapter";
          const size = isChapter ? 8 : 5;
          let color: string;

          if (isChapter) {
            color = "#64748b";
          } else if (node.insight_type) {
            color = INSIGHT_COLORS[node.insight_type] || "#64748b";
          } else {
            color = "#64748b";
          }

          const label = isChapter
            ? node.label
            : (node.label || "").replace(/_/g, " ");

          graph.addNode(node.id, {
            label,
            size,
            color,
            x: Math.random() * 100,
            y: Math.random() * 100,
            nodeType: node.type,
            insightType: node.insight_type || null,
            subject: node.subject || "",
            grade: node.grade || 0,
          });
        }

        const edgeSet = new Set<string>();
        for (const edge of edges) {
          const key = `${edge.source}→${edge.target}`;
          if (edgeSet.has(key)) continue;
          if (!graph.hasNode(edge.source) || !graph.hasNode(edge.target)) continue;
          edgeSet.add(key);
          graph.addEdge(edge.source, edge.target, {
            color: "#cbd5e1",
            size: 0.5,
          });
        }

        forceAtlas2.assign(graph, {
          iterations: 100,
          settings: {
            gravity: 1.5,
            scalingRatio: 3,
            strongGravityMode: false,
            barnesHutOptimize: true,
            barnesHutTheta: 0.5,
            adjustSizes: true,
            linLogMode: false,
            outboundAttractionDistribution: false,
            edgeWeightInfluence: 1,
            slowDown: 5,
          },
        });

        if (sigmaRef.current) {
          sigmaRef.current.kill();
          sigmaRef.current = null;
        }

        const renderer = new Sigma(graph, container, {
          renderLabels: true,
          renderEdgeLabels: false,
          labelFont: "Inter, system-ui, sans-serif",
          labelSize: 11,
          labelWeight: "600",
          labelColor: { color: "#0f172a" },
          labelRenderedSizeThreshold: 6,
          defaultEdgeColor: "#cbd5e1",
          defaultNodeColor: "#64748b",
          minCameraRatio: 0.1,
          maxCameraRatio: 10,
          stagePadding: 40,
        });

        sigmaRef.current = renderer;

        renderer.on("enterNode", ({ node }) => {
          setHoveredNode(node);
        });

        renderer.on("leaveNode", () => {
          setHoveredNode(null);
        });

        renderer.on("clickNode", ({ node }) => {
          const attrs = graph.getNodeAttributes(node);
          handleNodeClick(node, attrs.label as string, attrs.nodeType as string);
        });

        setLoading(false);
      } catch (e: unknown) {
        setError(e instanceof Error ? e.message : "Failed to load graph.");
        setLoading(false);
      }
    },
    [token, handleNodeClick]
  );

  useEffect(() => {
    if (!containerRef.current) return;
    buildGraph(containerRef.current);

    return () => {
      if (sigmaRef.current) {
        sigmaRef.current.kill();
        sigmaRef.current = null;
      }
    };
  }, [buildGraph]);

  // Hover highlight effect
  useEffect(() => {
    if (!sigmaRef.current) return;
    const sigma = sigmaRef.current;

    sigma.setSetting("nodeReducer", (node, data) => {
      const res = { ...data };
      const g = sigma.getGraph();
      if (!g) return res;
      if (hoveredNode) {
        if (node === hoveredNode || g.hasEdge(node, hoveredNode) || g.hasEdge(hoveredNode, node)) {
          res.highlighted = true;
        } else {
          res.color = `${data.color}44`;
          res.label = "";
        }
      }
      return res;
    });

    sigma.setSetting("edgeReducer", (edge, data) => {
      const res = { ...data };
      const g = sigma.getGraph();
      if (!g) return res;
      if (hoveredNode) {
        const source = g.source(edge);
        const target = g.target(edge);
        if (source !== hoveredNode && target !== hoveredNode) {
          res.hidden = true;
        } else {
          res.color = "#94a3b8";
          res.size = 1.5;
        }
      }
      return res;
    });

    sigma.refresh();
  }, [hoveredNode]);

  // ── Insight type helpers ──
  const insightColor = (type: string) => INSIGHT_COLORS[type] || "#94a3b8";
  const insightIcon = (type: string) => TYPE_ICON[type] || "info";

  return (
    <div style={{ position: "relative", marginBottom: "2rem" }}>
      <div
        style={{
          background: "#f8fafb",
          borderRadius: 20,
          overflow: "hidden",
          border: "1px solid #e2e8f0",
        }}
      >
        {/* Header */}
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            padding: "1rem 1.25rem 0.5rem",
            flexWrap: "wrap",
            gap: "0.5rem",
          }}
        >
          <div>
            <h2
              style={{
                margin: 0,
                fontSize: "1.25rem",
                fontWeight: 800,
                color: "#0f172a",
                letterSpacing: "-0.02em",
              }}
            >
              <span
                className="material-symbols-outlined"
                style={{ fontSize: 20, verticalAlign: "middle", marginRight: 6, color: "#13ecda" }}
              >
                hub
              </span>
              Knowledge Graph
            </h2>
            <p style={{ margin: "0.2rem 0 0", fontSize: "0.78rem", color: "#64748b" }}>
              Chapters → Concepts • Click any node to see insights
            </p>
          </div>

          {!loading && !error && (
            <div style={{ display: "flex", gap: "0.75rem", flexWrap: "wrap" }}>
              <LegendDot color="#64748b" label={`${stats.concepts - stats.withInsights} Not assessed`} />
              <LegendDot color="#10b981" label="Competency" />
              <LegendDot color="#f59e0b" label="Partial" />
              <LegendDot color="#ef4444" label="Misconception" />
            </div>
          )}
        </div>

        {/* Graph canvas */}
        <div
          ref={containerRef}
          style={{
            width: "100%",
            height: 460,
            position: "relative",
            cursor: loading ? "wait" : "grab",
          }}
        >
          {loading && (
            <div style={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center", color: "#64748b", fontSize: "0.9rem", fontWeight: 600 }}>
              Loading graph…
            </div>
          )}
          {error && (
            <div style={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center", color: "#ef4444", fontSize: "0.9rem", fontWeight: 600 }}>
              {error}
            </div>
          )}
        </div>

        {/* Stats bar */}
        {!loading && !error && (
          <div
            style={{
              display: "flex",
              justifyContent: "center",
              gap: "2rem",
              padding: "0.6rem 1.25rem 0.8rem",
              borderTop: "1px solid #e2e8f0",
            }}
          >
            <Stat label="Chapters" value={stats.chapters} />
            <Stat label="Concepts" value={stats.concepts} />
            <Stat label="With Insights" value={stats.withInsights} />
          </div>
        )}
      </div>

      {/* ── Insights Panel (overlay, closable) ── */}
      {panelOpen && panelNode && (
        <div
          style={{
            position: "absolute",
            top: 0,
            right: 0,
            width: 400,
            maxWidth: "100%",
            height: "100%",
            background: "#fff",
            borderLeft: "1px solid #e2e8f0",
            borderRadius: "0 20px 20px 0",
            boxShadow: "-8px 0 32px rgba(15, 23, 42, 0.1)",
            display: "flex",
            flexDirection: "column",
            zIndex: 10,
            overflow: "hidden",
          }}
        >
          {/* Panel header */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              padding: "0.85rem 1rem",
              borderBottom: "1px solid #e2e8f0",
              background: "#f8fafc",
              flexShrink: 0,
            }}
          >
            <div style={{ minWidth: 0 }}>
              <div style={{ fontSize: "0.62rem", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.1em", color: "#64748b", marginBottom: 2 }}>
                Active insights
              </div>
              <h3 style={{ margin: 0, fontSize: "1rem", fontWeight: 800, color: "#0f172a", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                {(panelNode.label || "").replace(/_/g, " ")}
              </h3>
            </div>
            <button
              onClick={() => { setPanelOpen(false); setPanelNode(null); }}
              aria-label="Close insights panel"
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                width: 32,
                height: 32,
                borderRadius: 8,
                border: "1px solid #e2e8f0",
                background: "#fff",
                cursor: "pointer",
                flexShrink: 0,
              }}
            >
              <span className="material-symbols-outlined" style={{ fontSize: 18, color: "#64748b" }}>close</span>
            </button>
          </div>

          {/* Panel body */}
          <div style={{ flex: 1, overflowY: "auto", padding: "0.75rem 1rem" }}>
            {panelLoading && (
              <p style={{ margin: 0, fontSize: "0.85rem", color: "#64748b", fontWeight: 600 }}>Loading insights…</p>
            )}

            {!panelLoading && panelError && (
              <p style={{ margin: 0, fontSize: "0.85rem", color: "#ef4444", fontWeight: 600 }}>{panelError}</p>
            )}

            {!panelLoading && !panelError && panelInsights.length === 0 && (
              <p style={{ margin: 0, fontSize: "0.85rem", color: "#64748b", fontWeight: 600 }}>
                No active insights for this {panelNode.type === "chapter" ? "chapter" : "concept"}.
              </p>
            )}

            {!panelLoading && !panelError && panelInsights.length > 0 && (
              <div style={{ display: "flex", flexDirection: "column", gap: "0.65rem" }}>
                {panelInsights.map((ins) => (
                  <div
                    key={ins.id}
                    style={{
                      border: "1px solid #e2e8f0",
                      borderLeft: `4px solid ${insightColor(ins.type)}`,
                      borderRadius: 12,
                      padding: "0.7rem 0.8rem",
                      background: "#f8fafc",
                    }}
                  >
                    {/* Type + category badges */}
                    <div style={{ display: "flex", alignItems: "center", gap: "0.4rem", flexWrap: "wrap", marginBottom: "0.3rem" }}>
                      <span className="material-symbols-outlined" style={{ fontSize: 14, color: insightColor(ins.type) }}>{insightIcon(ins.type)}</span>
                      <span style={{ fontSize: "0.65rem", fontWeight: 800, letterSpacing: "0.08em", textTransform: "uppercase", color: insightColor(ins.type) }}>
                        {ins.type.replace(/_/g, " ")}
                      </span>
                      <span style={{ fontSize: "0.6rem", fontWeight: 700, color: "#64748b", textTransform: "uppercase", letterSpacing: "0.08em", background: "#e2e8f0", borderRadius: 9999, padding: "0.1rem 0.4rem" }}>
                        {ins.category}
                      </span>
                    </div>

                    {/* Concept name */}
                    {ins.concept_name && (
                      <p style={{ margin: "0 0 0.25rem", fontSize: "0.72rem", fontWeight: 700, color: "#334155" }}>
                        {ins.concept_name.replace(/_/g, " ")}
                      </p>
                    )}

                    {/* Content */}
                    <div style={{ fontSize: "0.85rem", lineHeight: 1.55, color: "#0f172a" }}>
                      <TutorMarkdown text={ins.content} compact />
                    </div>

                    {/* Explain / Test buttons */}
                    {(ins.type === "PARTIAL_UNDERSTANDING" || ins.type === "MISCONCEPTION") && (
                      <div style={{ marginTop: "0.55rem", display: "flex", gap: "0.4rem", flexWrap: "wrap" }}>
                        <button
                          onClick={() => runExplain(ins.id)}
                          style={{
                            display: "inline-flex", alignItems: "center", gap: "0.2rem",
                            padding: "0.32rem 0.6rem", borderRadius: 8, border: "none",
                            background: "#13ecda", color: "#042b28", fontWeight: 800,
                            cursor: "pointer", fontFamily: "var(--font-display)", fontSize: "0.72rem",
                          }}
                        >
                          <span className="material-symbols-outlined" style={{ fontSize: 13 }}>bolt</span>
                          Explain
                        </button>
                        <button
                          onClick={() => runTest(ins.id)}
                          style={{
                            display: "inline-flex", alignItems: "center", gap: "0.2rem",
                            padding: "0.32rem 0.6rem", borderRadius: 8, border: "none",
                            background: "#3498db", color: "white", fontWeight: 800,
                            cursor: "pointer", fontFamily: "var(--font-display)", fontSize: "0.72rem",
                          }}
                        >
                          <span className="material-symbols-outlined" style={{ fontSize: 13 }}>quiz</span>
                          Test
                        </button>
                      </div>
                    )}

                    {/* Explain result */}
                    {explainById[ins.id] && (
                      <div style={{ marginTop: "0.5rem", borderRadius: 8, border: "1px solid #bae6fd", background: "#ecfeff", padding: "0.5rem 0.55rem" }}>
                        {explainById[ins.id].loading ? (
                          <p style={{ margin: 0, fontSize: "0.78rem", color: "#0f172a" }}>Generating explanation…</p>
                        ) : explainById[ins.id].error ? (
                          <p style={{ margin: 0, fontSize: "0.78rem", color: "#b91c1c" }}>{explainById[ins.id].error}</p>
                        ) : (
                          <>
                            <TutorMarkdown text={explainById[ins.id].text || ""} compact />
                            {!!explainById[ins.id].points?.length && (
                              <ul style={{ margin: "0.3rem 0 0", paddingLeft: "0.9rem" }}>
                                {explainById[ins.id].points!.map((p, i) => (
                                  <li key={i} style={{ fontSize: "0.74rem", color: "#334155", marginBottom: "0.2rem" }}>
                                    <TutorMarkdown text={p} compact />
                                  </li>
                                ))}
                              </ul>
                            )}
                          </>
                        )}
                      </div>
                    )}

                    {/* Test MCQ */}
                    {testById[ins.id] && (
                      <div style={{ marginTop: "0.5rem", borderRadius: 8, border: "1px solid #bfdbfe", background: "#eff6ff", padding: "0.55rem" }}>
                        {testById[ins.id].loading ? (
                          <p style={{ margin: 0, fontSize: "0.78rem", color: "#0f172a" }}>Generating MCQ…</p>
                        ) : testById[ins.id].error ? (
                          <p style={{ margin: 0, fontSize: "0.78rem", color: "#b91c1c" }}>{testById[ins.id].error}</p>
                        ) : (
                          <>
                            <TutorMarkdown text={testById[ins.id].question || ""} compact />
                            <div style={{ display: "grid", gap: "0.25rem", marginTop: "0.4rem" }}>
                              {Object.entries(testById[ins.id].options || {}).map(([k, v]) => (
                                <button
                                  key={k}
                                  onClick={() => setTestById((prev) => ({ ...prev, [ins.id]: { ...prev[ins.id], selected: k } }))}
                                  style={{
                                    textAlign: "left", borderRadius: 7,
                                    border: `1px solid ${(testById[ins.id].selected === k) ? "#2563eb" : "#cbd5e1"}`,
                                    background: (testById[ins.id].selected === k) ? "#dbeafe" : "white",
                                    padding: "0.32rem 0.42rem", cursor: "pointer",
                                    fontSize: "0.74rem", color: "#0f172a", fontFamily: "var(--font-body)",
                                  }}
                                >
                                  <span style={{ display: "inline-flex", gap: "0.3rem", alignItems: "flex-start" }}>
                                    <strong style={{ marginTop: 2 }}>{k}.</strong>
                                    <span style={{ flex: 1 }}><TutorMarkdown text={String(v)} compact /></span>
                                  </span>
                                </button>
                              ))}
                            </div>
                            <div style={{ marginTop: "0.4rem", display: "flex", gap: "0.4rem", alignItems: "center", flexWrap: "wrap" }}>
                              <button
                                onClick={() => evaluateTest(ins.id)}
                                disabled={!testById[ins.id].selected || !!testById[ins.id].evaluating}
                                style={{
                                  border: "none", borderRadius: 7, background: "#1d4ed8", color: "white",
                                  fontSize: "0.72rem", fontWeight: 800, padding: "0.3rem 0.6rem",
                                  cursor: (!testById[ins.id].selected || !!testById[ins.id].evaluating) ? "not-allowed" : "pointer",
                                  opacity: (!testById[ins.id].selected || !!testById[ins.id].evaluating) ? 0.6 : 1,
                                }}
                              >
                                {testById[ins.id].evaluating ? "Checking…" : "Submit Test"}
                              </button>
                              {testById[ins.id].done && (
                                <span style={{ fontSize: "0.68rem", color: "#065f46", fontWeight: 700 }}>
                                  Reconciled and saved.
                                </span>
                              )}
                            </div>
                            {!!testById[ins.id].feedback && (
                              <div style={{ marginTop: "0.35rem", fontSize: "0.74rem", color: "#1e3a8a" }}>
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
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div style={{ textAlign: "center" }}>
      <p style={{ margin: 0, fontSize: "1.5rem", fontWeight: 900, color: "#0f172a" }}>{value}</p>
      <p style={{ margin: 0, fontSize: "0.68rem", color: "#64748b", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.08em" }}>
        {label}
      </p>
    </div>
  );
}

function LegendDot({ color, label }: { color: string; label: string }) {
  return (
    <div style={{ display: "inline-flex", alignItems: "center", gap: 5 }}>
      <span
        style={{
          width: 8,
          height: 8,
          borderRadius: "50%",
          background: color,
          display: "inline-block",
          flexShrink: 0,
        }}
      />
      <span style={{ fontSize: "0.68rem", color: "#94a3b8", fontWeight: 600 }}>{label}</span>
    </div>
  );
}
