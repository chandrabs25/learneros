"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import Graph from "graphology";
import forceAtlas2 from "graphology-layout-forceatlas2";
import Sigma from "sigma";

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

const INSIGHT_COLORS: Record<string, string> = {
  COMPETENCY: "#10b981",
  PARTIAL_UNDERSTANDING: "#f59e0b",
  MISCONCEPTION: "#ef4444",
};

const SUBJECT_COLORS: Record<string, string> = {
  physics: "#3b82f6",
  chemistry: "#8b5cf6",
  biology: "#06b6d4",
  mathematics: "#f97316",
};

function getSubjectColor(subject: string | undefined): string {
  if (!subject) return "#64748b";
  return SUBJECT_COLORS[subject.toLowerCase()] || "#64748b";
}

export default function InsightsGraph({ token, onConceptClick }: InsightsGraphProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const sigmaRef = useRef<Sigma | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [hoveredNode, setHoveredNode] = useState<string | null>(null);
  const [stats, setStats] = useState({ chapters: 0, concepts: 0, withInsights: 0 });

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

        // Stats
        const chapterCount = nodes.filter((n) => n.type === "chapter").length;
        const conceptCount = nodes.filter((n) => n.type === "concept").length;
        const withInsights = nodes.filter(
          (n) => n.type === "concept" && n.insight_type
        ).length;
        setStats({ chapters: chapterCount, concepts: conceptCount, withInsights });

        // Build graphology graph
        const graph = new Graph();

        for (const node of nodes) {
          const isChapter = node.type === "chapter";
          const size = isChapter ? 8 : 5;
          let color: string;

          if (isChapter) {
            color = "#64748b"; // Grey for all chapters
          } else if (node.insight_type) {
            color = INSIGHT_COLORS[node.insight_type] || "#64748b";
          } else {
            color = "#64748b"; // Grey for concepts without insights
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
            type: isChapter ? "circle" : "circle",
            // Store metadata for hover/click
            nodeType: node.type,
            insightType: node.insight_type || null,
            subject: node.subject || "",
            grade: node.grade || 0,
          });
        }

        // Deduplicate edges
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

        // Run ForceAtlas2 layout
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

        // Cleanup previous instance
        if (sigmaRef.current) {
          sigmaRef.current.kill();
          sigmaRef.current = null;
        }

        // Create sigma renderer
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
          nodeReducer: (node, data) => {
            const res = { ...data };
            if (hoveredNode) {
              if (node === hoveredNode || graph.hasEdge(node, hoveredNode) || graph.hasEdge(hoveredNode, node)) {
                res.highlighted = true;
              } else {
                res.color = `${data.color}44`;
                res.label = "";
              }
            }
            return res;
          },
          edgeReducer: (edge, data) => {
            const res = { ...data };
            if (hoveredNode) {
              const source = graph.source(edge);
              const target = graph.target(edge);
              if (source !== hoveredNode && target !== hoveredNode) {
                res.hidden = true;
              } else {
                res.color = "#94a3b8";
                res.size = 1.5;
              }
            }
            return res;
          },
        });

        sigmaRef.current = renderer;

        // Event handlers
        renderer.on("enterNode", ({ node }) => {
          setHoveredNode(node);
          renderer.refresh();
        });

        renderer.on("leaveNode", () => {
          setHoveredNode(null);
          renderer.refresh();
        });

        renderer.on("clickNode", ({ node }) => {
          const attrs = graph.getNodeAttributes(node);
          if (attrs.nodeType === "concept" && onConceptClick) {
            onConceptClick(node);
          }
        });

        setLoading(false);
      } catch (e: unknown) {
        setError(e instanceof Error ? e.message : "Failed to load graph.");
        setLoading(false);
      }
    },
    [token, onConceptClick]
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

  // Keep hover state in sync with sigma reducers
  useEffect(() => {
    if (sigmaRef.current) {
      sigmaRef.current.setSetting("nodeReducer", (node, data) => {
        const res = { ...data };
        const graph = sigmaRef.current?.getGraph();
        if (!graph) return res;

        if (hoveredNode) {
          if (
            node === hoveredNode ||
            graph.hasEdge(node, hoveredNode) ||
            graph.hasEdge(hoveredNode, node)
          ) {
            res.highlighted = true;
          } else {
            res.color = `${data.color}44`;
            res.label = "";
          }
        }
        return res;
      });

      sigmaRef.current.setSetting("edgeReducer", (edge, data) => {
        const res = { ...data };
        const graph = sigmaRef.current?.getGraph();
        if (!graph) return res;

        if (hoveredNode) {
          const source = graph.source(edge);
          const target = graph.target(edge);
          if (source !== hoveredNode && target !== hoveredNode) {
            res.hidden = true;
          } else {
            res.color = "#94a3b8";
            res.size = 1.5;
          }
        }
        return res;
      });

      sigmaRef.current.refresh();
    }
  }, [hoveredNode]);

  return (
    <div
      style={{
        background: "#f8fafb",
        borderRadius: 20,
        overflow: "hidden",
        marginBottom: "2rem",
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
            Chapters → Concepts • Click a concept to see insights
          </p>
        </div>

        {!loading && !error && (
          <div style={{ display: "flex", gap: "0.75rem", flexWrap: "wrap" }}>
            <LegendDot color="#475569" label={`${stats.concepts - stats.withInsights} Not assessed`} />
            <LegendDot color="#10b981" label="Competency" />
            <LegendDot color="#f59e0b" label="Partial" />
            <LegendDot color="#ef4444" label="Misconception" />
          </div>
        )}
      </div>

      {/* Graph container */}
      <div
        ref={containerRef}
        style={{
          width: "100%",
          height: 460,
          position: "relative",
          cursor: loading ? "wait" : "default",
        }}
      >
        {loading && (
          <div
            style={{
              position: "absolute",
              inset: 0,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "#64748b",
              fontSize: "0.9rem",
              fontWeight: 600,
            }}
          >
            Loading graph…
          </div>
        )}
        {error && (
          <div
            style={{
              position: "absolute",
              inset: 0,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "#ef4444",
              fontSize: "0.9rem",
              fontWeight: 600,
            }}
          >
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



function LegendDot({ color, label, square = false }: { color: string; label: string; square?: boolean }) {
  return (
    <div style={{ display: "inline-flex", alignItems: "center", gap: 5 }}>
      <span
        style={{
          width: square ? 10 : 8,
          height: square ? 10 : 8,
          borderRadius: square ? 2 : "50%",
          background: color,
          display: "inline-block",
          flexShrink: 0,
        }}
      />
      <span style={legendLabelStyle}>{label}</span>
    </div>
  );
}

const legendLabelStyle: React.CSSProperties = {
  fontSize: "0.68rem",
  color: "#94a3b8",
  fontWeight: 600,
};
