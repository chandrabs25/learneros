"use client";

import { useEffect, useState, useMemo } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/lib/auth-context";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface GraphNode {
    id: string;
    label: string;
    number?: string;
    type: "section" | "concept";
    insight?: {
        type: string;
        category: string;
        content: string;
    } | null;
}

interface GraphEdge {
    source: string;
    target: string;
    type: "NEXT" | "REQUIRES";
}

interface InsightItem {
    id?: string;
    type: string;
    category: string;
    content: string;
    source_id?: string;
    concept_id?: string;
    created_at?: string;
    is_active?: boolean;
    source_title?: string;
}

interface ChapterMeta {
    id: string;
    title: string;
}

export default function KnowledgeGraphPage() {
    const params = useParams();
    const router = useRouter();
    const grade = params.grade as string;
    const subject = params.subject as string;
    const chapter = params.chapter as string;
    const { getIdToken } = useAuth();

    const chapterId = `ncert:${subject}:${grade}:${chapter}`;

    const [nodes, setNodes] = useState<GraphNode[]>([]);
    const [edges, setEdges] = useState<GraphEdge[]>([]);
    const [loading, setLoading] = useState(true);
    const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
    const [panelInsights, setPanelInsights] = useState<InsightItem[]>([]);
    const [panelLoading, setPanelLoading] = useState(false);
    const [chapterTitle, setChapterTitle] = useState("");
    const [chapterTitles, setChapterTitles] = useState<Record<string, string>>({});
    const [animationUrl, setAnimationUrl] = useState<string | null>(null);

    // Fetch graph data
    useEffect(() => {
        fetch(`${API_URL}/api/chapters/${chapterId}/graph`)
            .then((r) => r.json())
            .then((data) => {
                const loadedNodes = data.nodes || [];
                setNodes(loadedNodes);
                setEdges(data.edges || []);
                setLoading(false);

                // Auto-select chapter node
                const chNode = loadedNodes.find((n: GraphNode) => n.id === chapterId);
                if (chNode) {
                    handleNodeClick(chNode);
                } else {
                    // Fallback stub if node not explicitly in graph
                    handleNodeClick({
                        id: chapterId,
                        label: `Chapter ${chapter}`,
                        type: "section",
                        insight: null
                    });
                }
            })
            .catch(() => setLoading(false));

        // Get chapter title
        const subjectName = subject.charAt(0).toUpperCase() + subject.slice(1);
        fetch(`${API_URL}/api/grades/${grade}/subjects/${subjectName}/chapters`)
            .then((r) => r.json())
            .then((chapters) => {
                const list: ChapterMeta[] = Array.isArray(chapters) ? chapters : [];
                const map: Record<string, string> = {};
                for (const ch of list) {
                    if (ch?.id) map[ch.id] = ch.title || "";
                }
                setChapterTitles(map);
                const ch = list.find((c) => c.id === chapterId);
                if (ch) setChapterTitle(ch.title || `Chapter ${chapter}`);
            })
            .catch(() => { });
    }, [chapterId, grade, subject, chapter]);

    // Separate node types
    const conceptNodes = useMemo(() => nodes.filter((n) => n.type === "concept"), [nodes]);

    // Position nodes radially around center
    const nodePositions = useMemo(() => {
        const positions: Record<string, { x: number; y: number }> = {};
        const centerX = 50;
        const centerY = 50;

        // Chapter node at center
        positions["__chapter__"] = { x: centerX, y: centerY };

        // Concept nodes arranged in a circle
        const count = conceptNodes.length;
        const radius = Math.min(30, 15 + count * 2);
        conceptNodes.forEach((node, i) => {
            const angle = (2 * Math.PI * i) / count - Math.PI / 2;
            positions[node.id] = {
                x: centerX + radius * Math.cos(angle),
                y: centerY + radius * Math.sin(angle),
            };
        });

        return positions;
    }, [conceptNodes]);

    // Handle node click
    const handleNodeClick = async (node: GraphNode | null) => {
        setSelectedNode(node);
        if (!node) return;

        setPanelLoading(true);
        setPanelInsights([]);

        try {
            const token = await getIdToken();
            const headers: Record<string, string> = {};
            if (token) headers["Authorization"] = `Bearer ${token}`;

            if (node.type === "concept") {
                // Fetch concept insight log
                const res = await fetch(`${API_URL}/api/students/me/insights/concept/${node.id}`, {
                    headers,
                });
                if (res.ok) {
                    const data = await res.json();
                    const active = Array.isArray(data)
                        ? data.filter((ins: InsightItem) => ins.is_active !== false)
                        : [];
                    setPanelInsights(active);
                } else {
                    // Fallback: use inline insight from graph data
                    if (node.insight) {
                        setPanelInsights([{
                            type: node.insight.type,
                            category: node.insight.category,
                            content: node.insight.content,
                            concept_id: node.id,
                        }]);
                    }
                }
            } else {
                // Chapter/section: fetch all chapter insights
                const res = await fetch(`${API_URL}/api/students/me/insights?chapter_id=${chapterId}`, {
                    headers,
                });
                if (res.ok) {
                    const data = await res.json();
                    setPanelInsights(Array.isArray(data) ? data : []);
                } else {
                    // Fallback: gather inline insights from all nodes
                    const inlineInsights = nodes
                        .filter((n) => n.insight)
                        .map((n) => ({
                            type: n.insight!.type,
                            category: n.insight!.category,
                            content: n.insight!.content,
                            source_id: n.type === "section" ? n.id : undefined,
                            concept_id: n.type === "concept" ? n.id : undefined,
                        }));
                    setPanelInsights(inlineInsights);
                }
            }
        } catch {
            // Use inline insights as fallback
            if (node.insight) {
                setPanelInsights([{
                    type: node.insight.type,
                    category: node.insight.category,
                    content: node.insight.content,
                }]);
            }
        }
        setPanelLoading(false);
    };

    // Select chapter node by default
    const handleChapterClick = () => {
        handleNodeClick({
            id: chapterId,
            label: chapterTitle || `Chapter ${chapter}`,
            type: "section",
            insight: null,
        });
    };

    const insightColor = (type: string) => {
        switch (type) {
            case "COMPETENCY": return "#10b981";
            case "PARTIAL_UNDERSTANDING": return "#f59e0b";
            case "MISCONCEPTION": return "#ef4444";
            case "TAUGHT": return "#3b82f6";
            default: return "#94a3b8";
        }
    };

    const insightIcon = (type: string) => {
        switch (type) {
            case "COMPETENCY": return "check_circle";
            case "PARTIAL_UNDERSTANDING": return "help";
            case "MISCONCEPTION": return "error";
            case "TAUGHT": return "school";
            default: return "info";
        }
    };

    const parseChapterIdFromSource = (sourceId?: string) => {
        if (!sourceId) return null;
        const parts = sourceId.split(":");
        if (parts.length < 4) return null;
        return `${parts[0]}:${parts[1]}:${parts[2]}:${parts[3]}`;
    };

    const chapterInsights = useMemo(() => {
        if (selectedNode?.type !== "concept") return [];
        const groups: Record<string, { chapterId: string; chapterLabel: string; items: InsightItem[] }> = {};
        const order: string[] = [];
        for (const ins of panelInsights) {
            const chapterIdFromSource = parseChapterIdFromSource(ins.source_id) || chapterId;
            const chapterNum = chapterIdFromSource.split(":")[3] || "?";
            const chapterLabel = chapterTitles[chapterIdFromSource] || `Chapter ${chapterNum}`;
            if (!groups[chapterIdFromSource]) {
                groups[chapterIdFromSource] = {
                    chapterId: chapterIdFromSource,
                    chapterLabel,
                    items: [],
                };
                order.push(chapterIdFromSource);
            }
            groups[chapterIdFromSource].items.push(ins);
        }
        return order.map((key) => groups[key]);
    }, [panelInsights, selectedNode?.type, chapterId, chapterTitles]);

    if (loading) {
        return (
            <div className="kg-page">
                <div className="kg-loading">
                    <div className="spinner" />
                    <p>Loading Knowledge Graph...</p>
                </div>
            </div>
        );
    }

    return (
        <div className="kg-page">

            <div className="kg-layout">
                {/* Graph Canvas */}
                <div
                    className="kg-canvas"
                    style={{ width: selectedNode ? 'calc(100% - 440px)' : '100%', flex: 'none' }}
                >
                    {/* Back to Chapter button */}
                    <Link
                        href={`/${grade}/${subject}`}
                        className="kg-back-btn"
                        style={{ position: "absolute", top: 16, left: 16, zIndex: 10 }}
                    >
                        <span className="material-symbols-outlined" style={{ fontSize: "1rem" }}>arrow_back</span>
                        Back to Textbook
                    </Link>

                    {/* Instructional Text */}
                    <div style={{
                        position: "absolute",
                        top: 16,
                        left: "50%",
                        transform: "translateX(-50%)",
                        zIndex: 10,
                        background: "rgba(255, 255, 255, 0.9)",
                        backdropFilter: "blur(8px)",
                        padding: "8px 16px",
                        borderRadius: "9999px",
                        border: "1px solid rgba(0, 0, 0, 0.08)",
                        boxShadow: "0 4px 12px rgba(0, 0, 0, 0.05)",
                        display: "flex",
                        alignItems: "center",
                        gap: "8px",
                        color: "var(--black)",
                        fontSize: "0.875rem",
                        fontWeight: 600,
                        pointerEvents: "none",
                        animation: "kg-fade-in 1s ease-out 2s both"
                    }}>
                        <span className="material-symbols-outlined" style={{ fontSize: "1.25rem", color: "var(--primary)" }}>info</span>
                        Select any node to view insights & 3D animations
                    </div>
                    {/* SVG Edges & Particles */}
                    <svg className="kg-edges">
                        <defs>
                            <filter id="nodeGlow" x="-50%" y="-50%" width="200%" height="200%">
                                <feGaussianBlur stdDeviation="3" result="blur" />
                                <feComposite in="SourceGraphic" in2="blur" operator="over" />
                            </filter>
                        </defs>
                        {conceptNodes.map((cNode, i) => {
                            const from = nodePositions["__chapter__"];
                            const to = nodePositions[cNode.id];
                            if (!from || !to) return null;

                            // Edges start drawing AFTER all nodes have appeared.
                            // The chapter node pops in instantly (0s).
                            // The concept nodes pop in between 0.4s and 1.2s.
                            // Thus, edges start at 1.4s + stagger.
                            const edgeDelay = 1.4 + (i * 0.15);

                            const particleDur = 4 + (i % 2); // 4s or 5s

                            // Particles start a little after the edge lines finish drawing (which takes ~2s).
                            const particleDelay = edgeDelay + 2.0;

                            return (
                                <g key={cNode.id}>
                                    {/* The connecting line */}
                                    <line
                                        x1={`${from.x}%`}
                                        y1={`${from.y}%`}
                                        x2={`${to.x}%`}
                                        y2={`${to.y}%`}
                                        className="kg-edge"
                                        style={{ animationDelay: `${edgeDelay}s` }}
                                    />
                                    {/* Traveling Energy Particle */}
                                    <circle r="2.5" fill="var(--primary)" filter="url(#nodeGlow)" opacity="0">
                                        <animate attributeName="cx" values={`${from.x}%;${to.x}%`} dur={`${particleDur}s`} begin={`${particleDelay}s`} repeatCount="indefinite" />
                                        <animate attributeName="cy" values={`${from.y}%;${to.y}%`} dur={`${particleDur}s`} begin={`${particleDelay}s`} repeatCount="indefinite" />
                                        <animate attributeName="opacity" values="0;1;1;0" keyTimes="0;0.1;0.9;1" dur={`${particleDur}s`} begin={`${particleDelay}s`} repeatCount="indefinite" fill="freeze" />
                                    </circle>
                                </g>
                            );
                        })}
                    </svg>

                    {/* Chapter Node (center) */}
                    <div
                        className={`kg-node kg-node--chapter ${selectedNode?.id === chapterId ? "kg-node--selected" : ""}`}
                        style={{
                            left: `${nodePositions["__chapter__"]?.x ?? 50}%`,
                            top: `${nodePositions["__chapter__"]?.y ?? 50}%`,
                        }}
                        onClick={handleChapterClick}
                    >
                        <span className="material-symbols-outlined kg-node-icon">lightbulb</span>
                        <div className="kg-node-label">
                            <p className="kg-node-name">{chapterTitle || `Chapter ${chapter}`}</p>
                            <p className="kg-node-type">CHAPTER {chapter}</p>
                        </div>
                    </div>

                    {/* Concept Nodes */}
                    {conceptNodes.map((cNode) => {
                        const pos = nodePositions[cNode.id];
                        if (!pos) return null;
                        const isSelected = selectedNode?.id === cNode.id;
                        const hasInsight = !!cNode.insight;
                        return (
                            <div
                                key={cNode.id}
                                className={`kg-node kg-node--concept ${isSelected ? "kg-node--selected" : ""} ${hasInsight ? "kg-node--has-insight" : ""}`}
                                style={{ left: `${pos.x}%`, top: `${pos.y}%` }}
                                onClick={() => handleNodeClick(cNode)}
                            >
                                <span className="material-symbols-outlined kg-node-icon">
                                    {cNode.insight ? insightIcon(cNode.insight.type) : "science"}
                                </span>
                                <div className="kg-node-label">
                                    <p className="kg-node-name">
                                        {(cNode.label || "").replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}
                                    </p>
                                </div>
                                {cNode.insight && (
                                    <span
                                        className="kg-node-badge"
                                        style={{ background: insightColor(cNode.insight.type) }}
                                    />
                                )}
                            </div>
                        );
                    })}

                    {/* Legend */}
                    <div className="kg-legend">
                        <div className="kg-legend-item">
                            <span className="kg-legend-dot kg-legend-dot--chapter" />
                            <span>Chapter</span>
                        </div>
                        <div className="kg-legend-item">
                            <span className="kg-legend-dot kg-legend-dot--concept" />
                            <span>Concept</span>
                        </div>
                    </div>
                </div>

                {/* Insights Sidebar */}
                {selectedNode && (
                    <aside className="kg-panel">
                        <div className="kg-panel-inner">
                            <div className="kg-panel-header">
                                <div className="kg-panel-header-left">
                                    <span className="kg-panel-badge">INSIGHTS</span>
                                    <h3 className="kg-panel-title">Node Profile</h3>
                                </div>
                                <button
                                    onClick={() => setSelectedNode(null)}
                                    className="kg-panel-close"
                                >
                                    <span className="material-symbols-outlined">close</span>
                                </button>
                            </div>

                            <h2 className="kg-panel-node-name">
                                {selectedNode.type === "concept"
                                    ? (selectedNode.label || "").replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())
                                    : chapterTitle || `Chapter ${chapter}`}
                            </h2>
                            <p className="kg-panel-node-type">
                                {selectedNode.type === "concept" ? "Prerequisite Concept" : "Chapter Overview"}
                            </p>

                            {/* View Animation button – only for concept nodes */}
                            {selectedNode.type === "concept" && (() => {
                                const conceptKey = selectedNode.id.replace("concept:", "");
                                const animSrc = `${API_URL}/api/animations/${conceptKey}.html`;
                                return (
                                    <button
                                        className="kg-animation-btn"
                                        onClick={() => setAnimationUrl(animSrc)}
                                    >
                                        <span className="material-symbols-outlined" style={{ fontSize: '1.125rem' }}>play_circle</span>
                                        View 3D Animation
                                    </button>
                                );
                            })()}

                            {/* Insight stats */}
                            {panelInsights.length > 0 && !panelLoading && (
                                <div className="kg-panel-stats">
                                    <div className="kg-stat kg-stat--competency">
                                        <p className="kg-stat-label">Competency</p>
                                        <span className="kg-stat-count">
                                            {panelInsights.filter((i) => i.type === "COMPETENCY").length}
                                        </span>
                                    </div>
                                    <div className="kg-stat kg-stat--partial-understanding">
                                        <p className="kg-stat-label">Partial Understanding</p>
                                        <span className="kg-stat-count">
                                            {panelInsights.filter((i) => i.type === "PARTIAL_UNDERSTANDING").length}
                                        </span>
                                    </div>
                                    <div className="kg-stat kg-stat--misconception">
                                        <p className="kg-stat-label">Misconception</p>
                                        <span className="kg-stat-count">
                                            {panelInsights.filter((i) => i.type === "MISCONCEPTION").length}
                                        </span>
                                    </div>
                                </div>
                            )}

                            {/* Insights list */}
                            <div className="kg-panel-section-title">
                                <span className="material-symbols-outlined" style={{ fontSize: "1.125rem", color: "var(--primary)" }}>auto_awesome</span>
                                <span>Learning Insights</span>
                            </div>

                            <div className="kg-insights-list">
                                {panelLoading ? (
                                    <div className="kg-panel-loading">
                                        <div className="spinner" />
                                        <p>Loading insights...</p>
                                    </div>
                                ) : panelInsights.length === 0 ? (
                                    <div className="kg-panel-empty">
                                        <span className="material-symbols-outlined" style={{ fontSize: "2rem", color: "var(--border)" }}>
                                            psychology
                                        </span>
                                        <p>No insights yet for this node.</p>
                                        <p className="kg-panel-empty-sub">
                                            Complete lessons and exercises to build your knowledge profile.
                                        </p>
                                    </div>
                                ) : selectedNode.type === "concept" ? (
                                    chapterInsights.map((group) => (
                                        <div key={group.chapterId}>
                                            <div className="kg-panel-section-title" style={{ marginTop: "0.25rem" }}>
                                                <span className="material-symbols-outlined" style={{ fontSize: "1rem", color: "var(--text-muted)" }}>menu_book</span>
                                                <span>{`Chapter: ${group.chapterLabel}`}</span>
                                            </div>
                                            {group.items.map((ins, idx) => (
                                                <div
                                                    key={`${group.chapterId}-${ins.id || idx}`}
                                                    className="kg-insight-card"
                                                    style={{ borderLeftColor: insightColor(ins.type) }}
                                                >
                                                    <div className="kg-insight-header">
                                                        <span
                                                            className="material-symbols-outlined"
                                                            style={{ fontSize: "1rem", color: insightColor(ins.type) }}
                                                        >
                                                            {insightIcon(ins.type)}
                                                        </span>
                                                        <span
                                                            className="kg-insight-type"
                                                            style={{ color: insightColor(ins.type) }}
                                                        >
                                                            {ins.type.replace(/_/g, " ")}
                                                        </span>
                                                        {ins.category && (
                                                            <span className="kg-insight-category">{ins.category}</span>
                                                        )}
                                                    </div>
                                                    <p className="kg-insight-content">{ins.content}</p>
                                                    {(ins.source_title || ins.source_id) && (
                                                        <p className="kg-insight-content" style={{ marginTop: "0.35rem", fontSize: "0.74rem", opacity: 0.75 }}>
                                                            Subsection: {ins.source_title || ins.source_id}
                                                        </p>
                                                    )}
                                                </div>
                                            ))}
                                        </div>
                                    ))
                                ) : (
                                    panelInsights.map((ins, idx) => (
                                        <div
                                            key={idx}
                                            className="kg-insight-card"
                                            style={{ borderLeftColor: insightColor(ins.type) }}
                                        >
                                            <div className="kg-insight-header">
                                                <span
                                                    className="material-symbols-outlined"
                                                    style={{ fontSize: "1rem", color: insightColor(ins.type) }}
                                                >
                                                    {insightIcon(ins.type)}
                                                </span>
                                                <span
                                                    className="kg-insight-type"
                                                    style={{ color: insightColor(ins.type) }}
                                                >
                                                    {ins.type.replace(/_/g, " ")}
                                                </span>
                                                {ins.category && (
                                                    <span className="kg-insight-category">{ins.category}</span>
                                                )}
                                            </div>
                                            <p className="kg-insight-content">{ins.content}</p>
                                        </div>
                                    ))
                                )}
                            </div>
                        </div>
                    </aside>
                )}
            </div>

            {/* ── Fullscreen Animation Viewer Modal ── */}
            {animationUrl && (
                <div className="kg-anim-overlay" onClick={() => setAnimationUrl(null)}>
                    <div className="kg-anim-modal" onClick={(e) => e.stopPropagation()}>
                        <div className="kg-anim-header">
                            <div className="kg-anim-header-left">
                                <span className="material-symbols-outlined" style={{ fontSize: '1.25rem', color: 'var(--primary)' }}>view_in_ar</span>
                                <span className="kg-anim-title">Concept Animation</span>
                            </div>
                            <button className="kg-anim-close" onClick={() => setAnimationUrl(null)}>
                                <span className="material-symbols-outlined">close</span>
                            </button>
                        </div>
                        <iframe
                            src={animationUrl}
                            title="Concept Animation"
                            className="kg-anim-iframe"
                            allow="accelerometer; gyroscope"
                            sandbox="allow-scripts allow-same-origin"
                        />
                    </div>
                </div>
            )}
        </div>
    );
}
