"use client";

import { useEffect, useState, useMemo } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/lib/auth-context";
import TutorMarkdown from "@/components/TutorMarkdown";

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

interface ChapterMeta {
    id: string;
    title: string;
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
    const [explainById, setExplainById] = useState<Record<string, ExplainState>>({});
    const [testById, setTestById] = useState<Record<string, TestState>>({});
    const [lineageLoading, setLineageLoading] = useState(false);
    const [lineageError, setLineageError] = useState("");
    const [lineageData, setLineageData] = useState<LineagePayload | null>(null);

    const shouldShowActions = (ins: InsightItem) =>
        !!ins.id && (ins.type === "MISCONCEPTION" || ins.type === "PARTIAL_UNDERSTANDING");

    const fetchNodeInsights = async (node: GraphNode) => {
        const token = await getIdToken();
        const headers: Record<string, string> = {};
        if (token) headers["Authorization"] = `Bearer ${token}`;

        if (node.type === "concept") {
            const res = await fetch(`${API_URL}/api/students/me/insights/concept/${node.id}`, {
                headers,
            });
            if (res.ok) {
                const data = await res.json();
                const active = Array.isArray(data)
                    ? data.filter((ins: InsightItem) => ins.is_active !== false)
                    : [];
                setPanelInsights(active);
                return;
            }
            if (node.insight) {
                setPanelInsights([{
                    type: node.insight.type,
                    category: node.insight.category,
                    content: node.insight.content,
                    concept_id: node.id,
                }]);
            }
            return;
        }

        const res = await fetch(`${API_URL}/api/students/me/insights?chapter_id=${chapterId}`, {
            headers,
        });
        if (res.ok) {
            const data = await res.json();
            setPanelInsights(Array.isArray(data) ? data : []);
            return;
        }
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
    };

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
        setExplainById({});
        setTestById({});

        try {
            await fetchNodeInsights(node);
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
            if (selectedNode) {
                await fetchNodeInsights(selectedNode);
            }
        } catch (e: unknown) {
            setTestById((prev) => ({
                ...prev,
                [insightId]: { ...prev[insightId], evaluating: false, error: e instanceof Error ? e.message : "Failed to evaluate." },
            }));
        }
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

    useEffect(() => {
        let cancelled = false;
        const loadLineage = async () => {
            if (!selectedNode || selectedNode.type !== "concept") {
                setLineageData(null);
                setLineageError("");
                setLineageLoading(false);
                return;
            }
            setLineageLoading(true);
            setLineageError("");
            try {
                const res = await fetch(
                    `${API_URL}/api/concepts/${encodeURIComponent(selectedNode.id)}/lineage?chapter_limit=60`,
                );
                const data = await res.json();
                if (!res.ok) throw new Error(data?.detail || `HTTP ${res.status}`);
                if (!cancelled) setLineageData(data);
            } catch (e: unknown) {
                if (!cancelled) {
                    setLineageData(null);
                    setLineageError(e instanceof Error ? e.message : "Failed to load concept lineage.");
                }
            } finally {
                if (!cancelled) setLineageLoading(false);
            }
        };
        loadLineage();
        return () => {
            cancelled = true;
        };
    }, [selectedNode]);

    const lineageNodePositions = useMemo(() => {
        const positions: Record<string, { x: number; y: number }> = {};
        if (!lineageData?.nodes?.length) return positions;
        const byType: Record<LineageNode["type"], LineageNode[]> = {
            concept: [],
            grade: [],
            subject: [],
            chapter: [],
        };
        for (const node of lineageData.nodes) byType[node.type].push(node);
        for (const t of (Object.keys(byType) as LineageNode["type"][])) {
            byType[t].sort((a, b) => (a.label || "").localeCompare(b.label || "", undefined, { sensitivity: "base" }));
        }

        const xMap: Record<LineageNode["type"], number> = {
            concept: 60,
            grade: 180,
            subject: 300,
            chapter: 430,
        };
        const yStart = 30;
        const yGap = 50;

        for (const type of (Object.keys(xMap) as LineageNode["type"][])) {
            byType[type].forEach((n, idx) => {
                positions[n.id] = { x: xMap[type], y: yStart + idx * yGap };
            });
        }
        return positions;
    }, [lineageData]);

    const handleLineageChapterClick = (node: LineageNode) => {
        if (node.type !== "chapter") return;
        const gradeValue = node.meta?.grade;
        const subjectSlug = node.meta?.subject_slug;
        const chapterNumber = node.meta?.chapter_number;
        if (!gradeValue || !subjectSlug || !chapterNumber) return;
        router.push(`/${encodeURIComponent(gradeValue)}/${encodeURIComponent(subjectSlug)}/${encodeURIComponent(chapterNumber)}`);
    };

    const renderInsightActions = (ins: InsightItem) => {
        if (!shouldShowActions(ins) || !ins.id) return null;
        const insightId = ins.id;
        const explainState = explainById[insightId];
        const testState = testById[insightId];
        return (
            <>
                <div style={{ marginTop: "0.6rem", display: "flex", gap: "0.45rem", flexWrap: "wrap" }}>
                    <button
                        onClick={() => runExplain(insightId)}
                        style={{
                            display: "inline-flex",
                            alignItems: "center",
                            gap: "0.25rem",
                            padding: "0.36rem 0.62rem",
                            borderRadius: 8,
                            border: "none",
                            background: "#13ecda",
                            color: "#042b28",
                            fontWeight: 800,
                            cursor: "pointer",
                            fontFamily: "var(--font-display)",
                            fontSize: "0.74rem",
                        }}
                    >
                        <span className="material-symbols-outlined" style={{ fontSize: 14 }}>bolt</span>
                        Explain
                    </button>
                    <button
                        onClick={() => runTest(insightId)}
                        style={{
                            display: "inline-flex",
                            alignItems: "center",
                            gap: "0.25rem",
                            padding: "0.36rem 0.62rem",
                            borderRadius: 8,
                            border: "none",
                            background: "#3498db",
                            color: "white",
                            fontWeight: 800,
                            cursor: "pointer",
                            fontFamily: "var(--font-display)",
                            fontSize: "0.74rem",
                        }}
                    >
                        <span className="material-symbols-outlined" style={{ fontSize: 14 }}>quiz</span>
                        Test
                    </button>
                </div>

                {explainState && (
                    <div style={{ marginTop: "0.55rem", borderRadius: 8, border: "1px solid #bae6fd", background: "#ecfeff", padding: "0.52rem 0.6rem" }}>
                        {explainState.loading ? (
                            <p style={{ margin: 0, fontSize: "0.78rem", color: "#0f172a" }}>Generating explanation...</p>
                        ) : explainState.error ? (
                            <p style={{ margin: 0, fontSize: "0.78rem", color: "#b91c1c" }}>{explainState.error}</p>
                        ) : (
                            <>
                                <TutorMarkdown text={explainState.text || ""} compact />
                                {!!explainState.points?.length && (
                                    <ul style={{ margin: "0.35rem 0 0", paddingLeft: "0.95rem" }}>
                                        {explainState.points!.map((p, i) => (
                                            <li key={i} style={{ fontSize: "0.74rem", color: "#334155", marginBottom: "0.22rem" }}>
                                                <TutorMarkdown text={p} compact />
                                            </li>
                                        ))}
                                    </ul>
                                )}
                            </>
                        )}
                    </div>
                )}

                {testState && (
                    <div style={{ marginTop: "0.55rem", borderRadius: 8, border: "1px solid #bfdbfe", background: "#eff6ff", padding: "0.6rem" }}>
                        {testState.loading ? (
                            <p style={{ margin: 0, fontSize: "0.78rem", color: "#0f172a" }}>Generating MCQ...</p>
                        ) : testState.error ? (
                            <p style={{ margin: 0, fontSize: "0.78rem", color: "#b91c1c" }}>{testState.error}</p>
                        ) : (
                            <>
                                <TutorMarkdown text={testState.question || ""} compact />
                                <div style={{ display: "grid", gap: "0.28rem", marginTop: "0.45rem" }}>
                                    {Object.entries(testState.options || {}).map(([k, v]) => (
                                        <button
                                            key={k}
                                            onClick={() => setTestById((prev) => ({ ...prev, [insightId]: { ...prev[insightId], selected: k } }))}
                                            style={{
                                                textAlign: "left",
                                                borderRadius: 7,
                                                border: `1px solid ${(testState.selected === k) ? "#2563eb" : "#cbd5e1"}`,
                                                background: (testState.selected === k) ? "#dbeafe" : "white",
                                                padding: "0.36rem 0.45rem",
                                                cursor: "pointer",
                                                fontSize: "0.74rem",
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
                                <div style={{ marginTop: "0.45rem", display: "flex", gap: "0.4rem", alignItems: "center", flexWrap: "wrap" }}>
                                    <button
                                        onClick={() => evaluateTest(insightId)}
                                        disabled={!testState.selected || !!testState.evaluating}
                                        style={{
                                            border: "none",
                                            borderRadius: 7,
                                            background: "#1d4ed8",
                                            color: "white",
                                            fontSize: "0.72rem",
                                            fontWeight: 800,
                                            padding: "0.32rem 0.62rem",
                                            cursor: (!testState.selected || !!testState.evaluating) ? "not-allowed" : "pointer",
                                            opacity: (!testState.selected || !!testState.evaluating) ? 0.6 : 1,
                                        }}
                                    >
                                        {testState.evaluating ? "Checking..." : "Submit Test"}
                                    </button>
                                    {testState.done && (
                                        <span style={{ fontSize: "0.7rem", color: "#065f46", fontWeight: 700 }}>
                                            Reconciled and saved.
                                        </span>
                                    )}
                                </div>
                                {!!testState.feedback && (
                                    <div style={{ marginTop: "0.38rem", fontSize: "0.74rem", color: "#1e3a8a" }}>
                                        <TutorMarkdown text={testState.feedback || ""} compact />
                                    </div>
                                )}
                            </>
                        )}
                    </div>
                )}
            </>
        );
    };

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
                        Select any node to view insights & animations
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
                                        View Animation
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

                            {/* Concept lineage graph */}
                            {selectedNode.type === "concept" && (
                                <div style={{ marginTop: "0.8rem", border: "1px solid var(--border)", borderRadius: 12, background: "#f8fafc", padding: "0.7rem" }}>
                                    <div style={{ display: "flex", alignItems: "center", gap: "0.4rem", marginBottom: "0.5rem" }}>
                                        <span className="material-symbols-outlined" style={{ fontSize: "1rem", color: "var(--text-muted)" }}>hub</span>
                                        <span style={{ fontWeight: 800, fontSize: "0.82rem", letterSpacing: "0.08em", textTransform: "uppercase", color: "var(--text-muted)" }}>
                                            Concept Lineage
                                        </span>
                                    </div>
                                    {lineageLoading ? (
                                        <p style={{ margin: 0, color: "var(--text-muted)", fontSize: "0.8rem" }}>Loading concept graph...</p>
                                    ) : lineageError ? (
                                        <p style={{ margin: 0, color: "#ef4444", fontSize: "0.8rem" }}>{lineageError}</p>
                                    ) : !lineageData || (lineageData.nodes || []).length <= 1 ? (
                                        <p style={{ margin: 0, color: "var(--text-muted)", fontSize: "0.8rem" }}>No lineage data available for this concept.</p>
                                    ) : (
                                        <>
                                            {lineageData.meta.truncated && (
                                                <p style={{ margin: "0 0 0.45rem 0", color: "#92400e", fontSize: "0.74rem", fontWeight: 700 }}>
                                                    Showing {lineageData.meta.chapter_returned} of {lineageData.meta.chapter_total} chapters.
                                                </p>
                                            )}
                                            <div style={{ overflowX: "auto", border: "1px solid #e2e8f0", borderRadius: 10, background: "#fff" }}>
                                                <svg width={500} height={Math.max(220, ((lineageData.nodes?.length || 0) + 2) * 32)}>
                                                    {(lineageData.edges || []).map((edge, i) => {
                                                        const from = lineageNodePositions[edge.source];
                                                        const to = lineageNodePositions[edge.target];
                                                        if (!from || !to) return null;
                                                        return (
                                                            <line
                                                                key={`${edge.source}-${edge.target}-${i}`}
                                                                x1={from.x + 36}
                                                                y1={from.y + 16}
                                                                x2={to.x - 36}
                                                                y2={to.y + 16}
                                                                stroke="#cbd5e1"
                                                                strokeWidth={1.1}
                                                            />
                                                        );
                                                    })}
                                                    {(lineageData.nodes || []).map((n) => {
                                                        const p = lineageNodePositions[n.id];
                                                        if (!p) return null;
                                                        const color =
                                                            n.type === "concept" ? "#f97316" :
                                                                n.type === "grade" ? "#0ea5e9" :
                                                                    n.type === "subject" ? "#8b5cf6" : "#10b981";
                                                        const isChapter = n.type === "chapter";
                                                        return (
                                                            <g key={n.id}>
                                                                <rect
                                                                    x={p.x - 36}
                                                                    y={p.y}
                                                                    width={72}
                                                                    height={30}
                                                                    rx={8}
                                                                    fill={isChapter ? "#ecfdf5" : "#ffffff"}
                                                                    stroke={color}
                                                                    strokeWidth={1.2}
                                                                    style={isChapter ? { cursor: "pointer" } : undefined}
                                                                    onClick={() => handleLineageChapterClick(n)}
                                                                />
                                                                <text
                                                                    x={p.x}
                                                                    y={p.y + 19}
                                                                    textAnchor="middle"
                                                                    fill="#0f172a"
                                                                    fontSize={10.5}
                                                                    fontWeight={700}
                                                                    style={isChapter ? { cursor: "pointer" } : undefined}
                                                                    onClick={() => handleLineageChapterClick(n)}
                                                                >
                                                                    {(n.label || "").length > 14 ? `${n.label.slice(0, 13)}…` : n.label}
                                                                </text>
                                                            </g>
                                                        );
                                                    })}
                                                </svg>
                                            </div>
                                            <p style={{ margin: "0.35rem 0 0", color: "var(--text-muted)", fontSize: "0.72rem" }}>
                                                Click a chapter node to open it.
                                            </p>
                                        </>
                                    )}
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
                                                    {renderInsightActions(ins)}
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
                                            {renderInsightActions(ins)}
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
