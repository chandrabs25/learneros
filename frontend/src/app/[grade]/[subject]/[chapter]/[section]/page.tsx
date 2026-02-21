"use client";

import { useEffect, useState, useMemo } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/lib/auth-context";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import "katex/dist/katex.min.css";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Subsection {
    id: string;
    number: string;
    title: string;
    content: string;
    content_type: string;
    worked_examples: { label: string; problem: string; solution: string }[];
    diagrams: { label: string; description: string }[];
    tables: { caption: string; headers: string[]; rows_json: string }[];
}

/* ── Content-type styling config ── */
const TYPE_CONFIG: Record<string, { icon: string; color: string; label: string }> = {
    explanation: { icon: "menu_book", color: "#3b82f6", label: "Explanation" },
    derivation: { icon: "function", color: "#8b5cf6", label: "Derivation" },
    definition: { icon: "sticky_note_2", color: "#14b8a6", label: "Definition" },
    law: { icon: "gavel", color: "#f59e0b", label: "Law" },
    application: { icon: "build", color: "#ef4444", label: "Application" },
    experiment: { icon: "science", color: "#22c55e", label: "Experiment" },
    theorem: { icon: "verified", color: "#6366f1", label: "Theorem" },
};

/* ── LaTeX-aware text renderer ── */
function RichText({ text }: { text: string }) {
    const parts = useMemo(() => {
        if (!text) return [];
        // Split on $...$ (inline math) and $$...$$ (display math)
        const regex = /(\$\$[\s\S]+?\$\$|\$[^$\n]+?\$)/g;
        const segments: { type: "text" | "inline-math" | "display-math"; value: string }[] = [];
        let lastIndex = 0;
        let match;

        while ((match = regex.exec(text)) !== null) {
            if (match.index > lastIndex) {
                segments.push({ type: "text", value: text.slice(lastIndex, match.index) });
            }
            const raw = match[0];
            if (raw.startsWith("$$")) {
                segments.push({ type: "display-math", value: raw.slice(2, -2).trim() });
            } else {
                segments.push({ type: "inline-math", value: raw.slice(1, -1).trim() });
            }
            lastIndex = match.index + raw.length;
        }
        if (lastIndex < text.length) {
            segments.push({ type: "text", value: text.slice(lastIndex) });
        }
        return segments;
    }, [text]);

    const [katex, setKatex] = useState<typeof import("katex") | null>(null);
    useEffect(() => {
        import("katex").then(setKatex);
    }, []);

    return (
        <>
            {parts.map((seg, i) => {
                if (seg.type === "text") {
                    // Split by newlines for paragraphs
                    return seg.value.split("\n\n").map((para, j) => (
                        <span key={`${i}-${j}`}>
                            {j > 0 && <br />}
                            {para}
                        </span>
                    ));
                }
                if (!katex) return <code key={i}>{seg.value}</code>;
                try {
                    const html = katex.renderToString(seg.value, {
                        throwOnError: false,
                        displayMode: seg.type === "display-math",
                    });
                    if (seg.type === "display-math") {
                        return (
                            <div
                                key={i}
                                style={{ margin: "1.5rem 0", textAlign: "center", overflowX: "auto" }}
                                dangerouslySetInnerHTML={{ __html: html }}
                            />
                        );
                    }
                    return <span key={i} dangerouslySetInnerHTML={{ __html: html }} />;
                } catch {
                    return <code key={i}>{seg.value}</code>;
                }
            })}
        </>
    );
}

interface SectionNavItem {
    id: string;
    number: string;
    title: string;
}

interface SubsectionInsight {
    id: string;
    type: string;
    category: string;
    content: string;
    created_at: string;
    source_id: string;
    concept_id: string | null;
    concept_name: string | null;
}

interface TutorMessage {
    role: "user" | "assistant";
    text: string;
    matchedCount?: number;
}

export default function SectionViewerPage() {
    const params = useParams();
    const router = useRouter();
    const grade = params.grade as string;
    const subject = params.subject as string;
    const chapter = params.chapter as string;
    const section = params.section as string;
    const { user, getIdToken } = useAuth();

    const [subsections, setSubsections] = useState<Subsection[]>([]);
    const [currentIndex, setCurrentIndex] = useState(0);
    const [loading, setLoading] = useState(true);
    const [conceptCount, setConceptCount] = useState(0);
    const [chapterExerciseCount, setChapterExerciseCount] = useState(0);
    const [chapterSections, setChapterSections] = useState<SectionNavItem[]>([]);
    const [insightsOpen, setInsightsOpen] = useState(false);
    const [insightsLoading, setInsightsLoading] = useState(false);
    const [insightsError, setInsightsError] = useState("");
    const [subsectionInsights, setSubsectionInsights] = useState<SubsectionInsight[]>([]);
    const [tutorOpen, setTutorOpen] = useState(false);
    const [tutorSessionId, setTutorSessionId] = useState<string>("");
    const [tutorInput, setTutorInput] = useState("");
    const [tutorSending, setTutorSending] = useState(false);
    const [tutorHistoryLoading, setTutorHistoryLoading] = useState(false);
    const [tutorMessages, setTutorMessages] = useState<TutorMessage[]>([
        { role: "assistant", text: "Ask me anything about this subsection. I will use the section context and your relevant active insights." },
    ]);

    const sectionId = `ncert:${subject}:${grade}:${chapter}:${section}`;
    const chapterId = `ncert:${subject}:${grade}:${chapter}`;

    useEffect(() => {
        fetch(`${API_URL}/api/sections/${sectionId}/subsections`)
            .then((r) => r.json())
            .then((data) => {
                setSubsections(Array.isArray(data) ? data : []);
                setLoading(false);
            })
            .catch(() => setLoading(false));

        // Check how many concept animations exist for this section
        fetch(`${API_URL}/api/sections/${sectionId}/concepts`)
            .then((r) => r.json())
            .then((data) => setConceptCount(Array.isArray(data) ? data.length : 0))
            .catch(() => setConceptCount(0));

        // Check how many end exercises are available for this section
        fetch(`${API_URL}/api/sections/${sectionId}/exercises`)
            .then((r) => r.json())
            .then((data) => setChapterExerciseCount(Array.isArray(data) ? data.length : 0))
            .catch(() => setChapterExerciseCount(0));

        // Fetch all sections in this chapter for sidebar nav
        fetch(`${API_URL}/api/chapters/${chapterId}/sections`)
            .then((r) => r.json())
            .then((data) => setChapterSections(
                Array.isArray(data) ? data.filter((s: SectionNavItem) => s.title?.toLowerCase() !== "exercises") : []
            ))
            .catch(() => setChapterSections([]));
    }, [sectionId, chapterId]);

    // Scroll to top when changing subsection
    useEffect(() => {
        window.scrollTo({ top: 0, behavior: "smooth" });
    }, [currentIndex]);

    /* ── Helper: extract section slug from section ID ── */
    const sectionSlug = (id: string) => {
        // e.g. "ncert:physics:11:4:4.1" → "4.1"
        const parts = id.split(":");
        return parts[parts.length - 1];
    };

    const current = subsections[currentIndex];

    const loadSubsectionInsights = async () => {
        if (!current?.id) return;
        if (!user) {
            setSubsectionInsights([]);
            setInsightsError("Sign in to view your subsection insights.");
            setInsightsLoading(false);
            return;
        }
        setInsightsLoading(true);
        setInsightsError("");
        try {
            const token = await getIdToken();
            const headers: Record<string, string> = {};
            if (token) headers.Authorization = `Bearer ${token}`;
            const res = await fetch(
                `${API_URL}/api/students/me/insights/subsection/${encodeURIComponent(current.id)}`,
                { headers }
            );
            const data = await res.json();
            if (!res.ok) throw new Error(data?.detail || `HTTP ${res.status}`);
            setSubsectionInsights(Array.isArray(data) ? data : []);
        } catch (e: unknown) {
            setSubsectionInsights([]);
            setInsightsError(e instanceof Error ? e.message : "Failed to load insights.");
        } finally {
            setInsightsLoading(false);
        }
    };

    const sendTutorMessage = async () => {
        const message = tutorInput.trim();
        if (!message || !current?.id || tutorSending) return;

        setTutorInput("");
        setTutorMessages((prev) => [...prev, { role: "user", text: message }]);
        setTutorSending(true);
        try {
            const token = await getIdToken();
            const headers: Record<string, string> = { "Content-Type": "application/json" };
            if (token) headers.Authorization = `Bearer ${token}`;

            const res = await fetch(`${API_URL}/api/sections/${encodeURIComponent(sectionId)}/tutor/chat`, {
                method: "POST",
                headers,
                body: JSON.stringify({
                    subsection_id: current.id,
                    message,
                    session_id: tutorSessionId || undefined,
                }),
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data?.detail || `HTTP ${res.status}`);
            if (!tutorSessionId && data?.session_id) setTutorSessionId(data.session_id);
            setTutorMessages((prev) => [
                ...prev,
                {
                    role: "assistant",
                    text: data?.response || "I couldn't generate a response.",
                    matchedCount: Array.isArray(data?.matched_insights) ? data.matched_insights.length : 0,
                },
            ]);
        } catch (e: unknown) {
            setTutorMessages((prev) => [
                ...prev,
                { role: "assistant", text: e instanceof Error ? e.message : "Failed to contact AI Tutor." },
            ]);
        } finally {
            setTutorSending(false);
        }
    };

    useEffect(() => {
        if (insightsOpen) {
            loadSubsectionInsights();
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [insightsOpen, current?.id, user]);

    useEffect(() => {
        if (!tutorOpen || !current?.id || !user) return;
        let cancelled = false;
        (async () => {
            setTutorHistoryLoading(true);
            try {
                const token = await getIdToken();
                if (!token) return;
                const res = await fetch(
                    `${API_URL}/api/sections/${encodeURIComponent(sectionId)}/tutor/session/latest?subsection_id=${encodeURIComponent(current.id)}`,
                    { headers: { Authorization: `Bearer ${token}` } }
                );
                const data = await res.json();
                if (!res.ok) throw new Error(data?.detail || `HTTP ${res.status}`);
                const history = Array.isArray(data?.messages) ? data.messages : [];
                if (!cancelled && data?.session_id && history.length > 0) {
                    setTutorSessionId(data.session_id);
                    setTutorMessages(history.map((m: { role: "user" | "assistant"; content: string }) => ({ role: m.role, text: m.content })));
                }
            } catch {
                // Keep current in-memory messages if loading fails.
            } finally {
                if (!cancelled) setTutorHistoryLoading(false);
            }
        })();
        return () => {
            cancelled = true;
        };
    }, [tutorOpen, current?.id, user, getIdToken, sectionId]);

    if (loading) {
        return (
            <div className="loading-container">
                <div className="spinner" />
                Loading content...
            </div>
        );
    }

    if (!current) {
        return <div className="loading-container">No content found for this section.</div>;
    }

    const typeCfg = TYPE_CONFIG[current.content_type] || TYPE_CONFIG.explanation;
    const validExamples = current.worked_examples?.filter((we) => we.label || we.problem) || [];
    const validDiagrams = current.diagrams?.filter((d) => d.description) || [];
    const validTables = current.tables?.filter((t) => t.caption || t.headers) || [];

    return (
        <div className="section-page-layout">
            {/* ────── Left sidebar: Chapter sections ────── */}
            <aside className="section-sidebar">
                <div className="section-sidebar-inner">
                    <h3 className="section-sidebar-heading">
                        <Link href={`/${grade}/${subject}/${chapter}`} style={{ color: "inherit", textDecoration: "none" }}>
                            Chapter {chapter}
                        </Link>
                    </h3>
                    <nav className="section-sidebar-nav">
                        {chapterSections.map((sec) => {
                            const slug = sectionSlug(sec.id);
                            const isCurrent = slug === section;
                            return (
                                <div key={sec.id}>
                                    <Link
                                        href={`/${grade}/${subject}/${chapter}/${slug}`}
                                        className={`section-sidebar-link${isCurrent ? " section-sidebar-link--active" : ""}`}
                                    >
                                        <span className="section-sidebar-dot" />
                                        <span>{sec.number}. {sec.title}</span>
                                    </Link>
                                    {/* Show subsections under the active section */}
                                    {isCurrent && subsections.length > 0 && (
                                        <div className="section-sidebar-subsections">
                                            {subsections.map((ss, idx) => (
                                                <button
                                                    key={ss.id}
                                                    onClick={() => setCurrentIndex(idx)}
                                                    className={`section-sidebar-subsection${idx === currentIndex ? " section-sidebar-subsection--active" : ""}`}
                                                >
                                                    <span className="section-sidebar-sub-dot" />
                                                    <span>{ss.title}</span>
                                                </button>
                                            ))}
                                        </div>
                                    )}
                                </div>
                            );
                        })}
                    </nav>

                    {/* Progress indicator */}
                    <div className="section-sidebar-progress">
                        <p className="section-sidebar-progress-label">Section Progress</p>
                        <div className="section-sidebar-progress-row">
                            <span className="section-sidebar-progress-value">
                                {Math.round(((currentIndex + 1) / subsections.length) * 100)}%
                            </span>
                            <span className="section-sidebar-progress-meta">
                                {currentIndex + 1} of {subsections.length}
                            </span>
                        </div>
                        <div className="section-sidebar-progress-track">
                            <div
                                className="section-sidebar-progress-fill"
                                style={{ width: `${((currentIndex + 1) / subsections.length) * 100}%` }}
                            />
                        </div>
                    </div>
                    {/* Knowledge Graph button */}
                    <button
                        onClick={() => router.push(`/${grade}/${subject}/${chapter}/graph`)}
                        style={{
                            display: "flex", alignItems: "center", gap: "0.5rem",
                            width: "100%", padding: "0.75rem 1rem",
                            background: "#0a0a0a", color: "white", border: "none",
                            borderRadius: "var(--radius)", fontWeight: 700,
                            fontSize: "0.8125rem", cursor: "pointer",
                            fontFamily: "var(--font-display)",
                            marginTop: "0.75rem",
                            transition: "background 0.15s ease",
                        }}
                        onMouseOver={(e) => (e.currentTarget.style.background = "#1a1a1a")}
                        onMouseOut={(e) => (e.currentTarget.style.background = "#0a0a0a")}
                    >
                        <span className="material-symbols-outlined" style={{ fontSize: "1.125rem" }}>hub</span>
                        Knowledge Graph
                    </button>
                </div>
            </aside>

            {/* ────── Main content ────── */}
            <div className="section-main-content">
                {/* Header */}
                <div style={{ marginBottom: "2.5rem" }}>
                    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "1.5rem" }}>
                        <nav className="breadcrumb">
                            <Link href="/">Hub</Link>
                            <span className="sep">›</span>
                            <Link href={`/${grade}/${subject}`}>
                                {subject.charAt(0).toUpperCase() + subject.slice(1)}
                            </Link>
                            <span className="sep">›</span>
                            <Link href={`/${grade}/${subject}/${chapter}`}>Chapter {chapter}</Link>
                            <span className="sep">›</span>
                            <span className="current">Section {section}</span>
                        </nav>

                        <button
                            onClick={() => router.push(`/${grade}/${subject}`)}
                            style={{
                                display: "flex", alignItems: "center", gap: "0.4rem",
                                padding: "0.5rem 0.875rem", background: "white",
                                border: "1px solid var(--border)", borderRadius: "999px",
                                fontSize: "0.75rem", fontWeight: 700, textTransform: "uppercase",
                                letterSpacing: "0.05em", color: "var(--text-secondary)",
                                cursor: "pointer", boxShadow: "0 2px 5px rgba(0,0,0,0.02)",
                                transition: "all 0.2s ease"
                            }}
                            onMouseOver={(e) => {
                                e.currentTarget.style.background = "#f8fafc";
                                e.currentTarget.style.borderColor = "#cbd5e1";
                            }}
                            onMouseOut={(e) => {
                                e.currentTarget.style.background = "white";
                                e.currentTarget.style.borderColor = "var(--border)";
                            }}
                        >
                            <span className="material-symbols-outlined" style={{ fontSize: "1rem" }}>arrow_back</span>
                            Back to Textbook
                        </button>
                    </div>

                    {/* Content type badge */}
                    <div style={{
                        display: "inline-flex", alignItems: "center", gap: "0.5rem",
                        padding: "0.3rem 0.75rem", borderRadius: "9999px",
                        background: `${typeCfg.color}15`, color: typeCfg.color,
                        fontSize: "0.6875rem", fontWeight: 700, textTransform: "uppercase",
                        letterSpacing: "0.12em", marginBottom: "1rem",
                    }}>
                        <span className="material-symbols-outlined" style={{ fontSize: "0.875rem" }}>
                            {typeCfg.icon}
                        </span>
                        {typeCfg.label}
                    </div>

                    <h1 className="font-display" style={{
                        fontSize: "2.5rem", fontWeight: 800, letterSpacing: "-0.03em",
                        lineHeight: 1.15, marginBottom: "0.75rem",
                    }}>
                        {current.title || `Section ${section}`}
                    </h1>
                    <p style={{ fontSize: "1rem", color: "var(--text-muted)" }}>
                        Subsection {currentIndex + 1} of {subsections.length}
                    </p>
                </div>

                {/* Content body */}
                <article style={{ fontSize: "1.0625rem", lineHeight: 1.85, color: "var(--text-secondary)" }}>
                    {current.content ? (
                        current.content.split("\n\n").map((para, i) => (
                            <div key={i} style={{ marginBottom: "1.25rem" }}>
                                <RichText text={para} />
                            </div>
                        ))
                    ) : (
                        <p style={{ color: "var(--text-muted)", fontStyle: "italic" }}>
                            Content for this subsection will be available soon.
                        </p>
                    )}
                </article>

                {/* Worked Examples */}
                {validExamples.length > 0 && (
                    <div style={{ marginTop: "2.5rem" }}>
                        <h3 className="font-display" style={{
                            fontSize: "0.75rem", fontWeight: 700, textTransform: "uppercase",
                            letterSpacing: "0.15em", color: "var(--text-muted)", marginBottom: "1rem",
                        }}>
                            <span className="material-symbols-outlined" style={{ fontSize: "1rem", verticalAlign: "middle", marginRight: "0.5rem" }}>edit_note</span>
                            Worked Examples
                        </h3>
                        {validExamples.map((we, i) => (
                            <div key={i} style={{
                                background: "var(--white)", borderLeft: "4px solid #8b5cf6",
                                borderRadius: "var(--radius)", padding: "1.5rem",
                                boxShadow: "0 2px 8px rgba(0,0,0,0.04)", marginBottom: "1.25rem",
                            }}>
                                {/* Label */}
                                <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "1rem" }}>
                                    <span className="material-symbols-outlined" style={{ color: "#8b5cf6", fontSize: "1.125rem" }}>verified</span>
                                    <h4 style={{ fontWeight: 700, fontSize: "0.9375rem" }}>{we.label || `Example ${i + 1}`}</h4>
                                </div>

                                {/* Problem */}
                                {we.problem && (
                                    <div style={{ marginBottom: "1rem" }}>
                                        <div style={{
                                            fontSize: "0.6875rem", fontWeight: 700, textTransform: "uppercase",
                                            letterSpacing: "0.1em", color: "var(--text-muted)", marginBottom: "0.5rem",
                                        }}>Problem</div>
                                        <div style={{
                                            fontSize: "0.9375rem", lineHeight: 1.75, color: "var(--text-secondary)",
                                            padding: "1rem", background: "#faf5ff", borderRadius: "8px",
                                        }}>
                                            <RichText text={we.problem} />
                                        </div>
                                    </div>
                                )}

                                {/* Solution */}
                                {we.solution && (
                                    <div>
                                        <div style={{
                                            fontSize: "0.6875rem", fontWeight: 700, textTransform: "uppercase",
                                            letterSpacing: "0.1em", color: "var(--text-muted)", marginBottom: "0.5rem",
                                        }}>Solution</div>
                                        <div style={{
                                            fontSize: "0.9375rem", lineHeight: 1.75, color: "var(--text-secondary)",
                                            padding: "1rem", background: "#f0fdf4", borderRadius: "8px",
                                            borderLeft: "3px solid #22c55e",
                                        }}>
                                            <RichText text={we.solution} />
                                        </div>
                                    </div>
                                )}
                            </div>
                        ))}
                    </div>
                )}

                {/* Diagrams */}
                {validDiagrams.length > 0 && (
                    <div style={{ marginTop: "2.5rem" }}>
                        <h3 className="font-display" style={{
                            fontSize: "0.75rem", fontWeight: 700, textTransform: "uppercase",
                            letterSpacing: "0.15em", color: "var(--text-muted)", marginBottom: "1rem",
                        }}>
                            <span className="material-symbols-outlined" style={{ fontSize: "1rem", verticalAlign: "middle", marginRight: "0.5rem" }}>image</span>
                            Diagrams &amp; Figures
                        </h3>
                        {validDiagrams.map((d, i) => (
                            <div key={i} style={{
                                background: "linear-gradient(135deg, #f0fdfa 0%, #f8fafb 100%)",
                                border: "1px solid rgba(20, 184, 166, 0.2)",
                                borderLeft: "4px solid var(--primary)",
                                borderRadius: "var(--radius)", padding: "1.5rem",
                                marginBottom: "1rem",
                            }}>
                                <div style={{ display: "flex", alignItems: "flex-start", gap: "1rem" }}>
                                    <span className="material-symbols-outlined" style={{
                                        fontSize: "1.5rem", color: "var(--primary)",
                                        background: "rgba(20,184,166,0.1)", borderRadius: "8px",
                                        padding: "0.5rem", flexShrink: 0,
                                    }}>insert_photo</span>
                                    <div>
                                        {d.label && (
                                            <h4 style={{ fontWeight: 700, fontSize: "0.9375rem", marginBottom: "0.5rem" }}>{d.label}</h4>
                                        )}
                                        <div style={{ fontSize: "0.9375rem", lineHeight: 1.75, color: "var(--text-secondary)" }}>
                                            <RichText text={d.description} />
                                        </div>
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                )}

                {/* Tables */}
                {validTables.length > 0 && (
                    <div style={{ marginTop: "2rem" }}>
                        {validTables.map((tbl, i) => {
                            let rows: string[][] = [];
                            try {
                                rows = typeof tbl.rows_json === "string" ? JSON.parse(tbl.rows_json) : tbl.rows_json || [];
                            } catch { /* ignore */ }

                            return (
                                <div key={i} style={{ marginBottom: "1.5rem" }}>
                                    {tbl.caption && (
                                        <h4 style={{
                                            fontSize: "0.8125rem", fontWeight: 700, color: "var(--text-muted)",
                                            textTransform: "uppercase", letterSpacing: "0.1em",
                                            marginBottom: "0.75rem",
                                        }}>{tbl.caption}</h4>
                                    )}
                                    <div style={{ overflowX: "auto", borderRadius: "var(--radius)", border: "1px solid var(--border)" }}>
                                        <table style={{
                                            width: "100%", borderCollapse: "collapse",
                                            fontSize: "0.875rem", fontFamily: "var(--font-body)",
                                        }}>
                                            {tbl.headers && tbl.headers.length > 0 && (
                                                <thead>
                                                    <tr>
                                                        {tbl.headers.map((h, j) => (
                                                            <th key={j} style={{
                                                                padding: "0.75rem 1rem", textAlign: "left",
                                                                fontWeight: 700, fontSize: "0.6875rem",
                                                                textTransform: "uppercase", letterSpacing: "0.1em",
                                                                background: "#f1f5f9", borderBottom: "2px solid var(--border)",
                                                                color: "var(--text)",
                                                            }}>
                                                                <RichText text={h} />
                                                            </th>
                                                        ))}
                                                    </tr>
                                                </thead>
                                            )}
                                            <tbody>
                                                {rows.map((row, ri) => (
                                                    <tr key={ri} style={{ borderBottom: "1px solid var(--border)" }}>
                                                        {row.map((cell, ci) => (
                                                            <td key={ci} style={{
                                                                padding: "0.625rem 1rem",
                                                                background: ri % 2 === 0 ? "white" : "#fafafa",
                                                                color: "var(--text-secondary)",
                                                            }}>
                                                                <RichText text={cell} />
                                                            </td>
                                                        ))}
                                                    </tr>
                                                ))}
                                            </tbody>
                                        </table>
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                )}
            </div>

            {/* Right-edge Insight tab + panel */}
            {!insightsOpen && (
                <button
                    className="section-insights-tab"
                    onClick={() => setInsightsOpen((v) => !v)}
                    aria-label="Open insights panel"
                >
                    <span className="material-symbols-outlined">auto_awesome</span>
                    <span className="section-insights-tab-label">Insights</span>
                </button>
            )}

            {insightsOpen && (
                <div className="section-insights-panel">
                    <div className="section-insights-panel-header">
                        <div>
                            <div className="section-insights-panel-kicker">Active insights</div>
                            <h3 className="section-insights-panel-title">
                                {current.title}
                            </h3>
                        </div>
                        <button
                            className="section-insights-panel-close"
                            onClick={() => setInsightsOpen(false)}
                            aria-label="Close insights panel"
                        >
                            <span className="material-symbols-outlined">close</span>
                        </button>
                    </div>

                    {insightsLoading && (
                        <div className="section-insights-panel-state">Loading insights…</div>
                    )}

                    {!insightsLoading && insightsError && (
                        <div className="section-insights-panel-state">{insightsError}</div>
                    )}

                    {!insightsLoading && !insightsError && subsectionInsights.length === 0 && (
                        <div className="section-insights-panel-state">
                            No active insights yet for this subsection.
                        </div>
                    )}

                    {!insightsLoading && !insightsError && subsectionInsights.length > 0 && (
                        <div className="section-insights-list">
                            {subsectionInsights.map((ins) => (
                                <div key={ins.id} className="section-insight-card">
                                    <div className="section-insight-card-top">
                                        <span className={`section-insight-type section-insight-type--${ins.type.toLowerCase()}`}>
                                            {ins.type.replace("_", " ")}
                                        </span>
                                        <span className="section-insight-category">{ins.category}</span>
                                    </div>
                                    <div className="section-insight-concept">
                                        {ins.concept_name || ins.concept_id || "General"}
                                    </div>
                                    <p className="section-insight-content">{ins.content}</p>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            )}

            {tutorOpen && (
                <div className="section-insights-panel" style={{ right: "20rem", width: "min(32rem, calc(100vw - 2rem))" }}>
                    <div className="section-insights-panel-header">
                        <div>
                            <div className="section-insights-panel-kicker">AI Tutor</div>
                            <h3 className="section-insights-panel-title">{current.title}</h3>
                        </div>
                        <button
                            className="section-insights-panel-close"
                            onClick={() => setTutorOpen(false)}
                            aria-label="Close tutor panel"
                        >
                            <span className="material-symbols-outlined">close</span>
                        </button>
                    </div>

                    <div style={{ display: "flex", flexDirection: "column", gap: "0.6rem", maxHeight: "50vh", overflowY: "auto", paddingRight: 4 }}>
                        {tutorHistoryLoading ? (
                            <div style={{ fontSize: "0.9rem", color: "#64748b" }}>Loading conversation...</div>
                        ) : tutorMessages.map((m, i) => (
                            <div
                                key={i}
                                style={{
                                    alignSelf: m.role === "user" ? "flex-end" : "flex-start",
                                    maxWidth: "92%",
                                    background: m.role === "user" ? "#0f172a" : "#f8fafc",
                                    color: m.role === "user" ? "white" : "#0f172a",
                                    border: m.role === "user" ? "none" : "1px solid #e2e8f0",
                                    borderRadius: 12,
                                    padding: "0.6rem 0.7rem",
                                    fontSize: "0.9rem",
                                    lineHeight: 1.5,
                                }}
                            >
                                <ReactMarkdown
                                    remarkPlugins={[remarkGfm]}
                                    components={{
                                        p: ({ children }) => <p style={{ margin: "0 0 0.55rem 0" }}>{children}</p>,
                                        ul: ({ children }) => <ul style={{ margin: "0.2rem 0 0.55rem 1.2rem" }}>{children}</ul>,
                                        ol: ({ children }) => <ol style={{ margin: "0.2rem 0 0.55rem 1.2rem" }}>{children}</ol>,
                                        code: ({ children }) => (
                                            <code style={{ background: "rgba(148,163,184,0.2)", borderRadius: 6, padding: "0.1rem 0.3rem" }}>{children}</code>
                                        ),
                                        pre: ({ children }) => (
                                            <pre style={{ background: "rgba(15,23,42,0.08)", borderRadius: 10, padding: "0.75rem", overflowX: "auto" }}>{children}</pre>
                                        ),
                                        table: ({ children }) => (
                                            <div style={{ overflowX: "auto", borderRadius: 8, border: "1px solid #cbd5e1", background: "white", marginBottom: "0.5rem" }}>
                                                <table style={{ borderCollapse: "collapse", minWidth: "100%", fontSize: "0.84rem", color: "#0f172a" }}>{children}</table>
                                            </div>
                                        ),
                                        th: ({ children }) => (
                                            <th style={{ textAlign: "left", padding: "0.42rem 0.5rem", borderBottom: "1px solid #cbd5e1", background: "#f8fafc", fontWeight: 700, whiteSpace: "nowrap" }}>{children}</th>
                                        ),
                                        td: ({ children }) => (
                                            <td style={{ padding: "0.38rem 0.5rem", borderTop: "1px solid #e2e8f0", verticalAlign: "top" }}>{children}</td>
                                        ),
                                    }}
                                >
                                    {m.text || ""}
                                </ReactMarkdown>
                                {m.role === "assistant" && typeof m.matchedCount === "number" && (
                                    <div style={{ marginTop: 6, fontSize: "0.68rem", color: "#64748b", textTransform: "uppercase", letterSpacing: "0.08em", fontWeight: 700 }}>
                                        {m.matchedCount} matched insight{m.matchedCount === 1 ? "" : "s"} used
                                    </div>
                                )}
                            </div>
                        ))}
                    </div>

                    <div style={{ marginTop: 12, display: "flex", gap: 8 }}>
                        <input
                            value={tutorInput}
                            onChange={(e) => setTutorInput(e.target.value)}
                            onKeyDown={(e) => {
                                if (e.key === "Enter") {
                                    e.preventDefault();
                                    sendTutorMessage();
                                }
                            }}
                            placeholder="Ask about this subsection..."
                            style={{
                                flex: 1,
                                borderRadius: 10,
                                border: "1px solid #cbd5e1",
                                padding: "0.6rem 0.7rem",
                                fontSize: "0.9rem",
                                outline: "none",
                                fontFamily: "var(--font-body)",
                            }}
                        />
                        <button
                            onClick={sendTutorMessage}
                            disabled={tutorSending || !tutorInput.trim()}
                            style={{
                                border: "none",
                                borderRadius: 10,
                                background: "#13ecda",
                                color: "#0a2e2b",
                                padding: "0.6rem 0.9rem",
                                fontWeight: 700,
                                cursor: tutorSending || !tutorInput.trim() ? "not-allowed" : "pointer",
                                opacity: tutorSending || !tutorInput.trim() ? 0.6 : 1,
                                fontFamily: "var(--font-display)",
                            }}
                        >
                            {tutorSending ? "..." : "Send"}
                        </button>
                    </div>
                </div>
            )}

            {/* ────── Floating Action Bar ────── */}
            <footer className="section-action-bar">
                <div style={{
                    width: "95%", maxWidth: "80rem",
                }}>
                    <div style={{
                        background: "rgba(255,255,255,0.92)", backdropFilter: "blur(16px)",
                        border: "1px solid rgba(0,0,0,0.08)", borderRadius: "var(--radius-lg)",
                        padding: "1rem", display: "flex", alignItems: "center", justifyContent: "space-between",
                        gap: "1rem", boxShadow: "0 20px 40px rgba(0,0,0,0.1)",
                    }}>
                        {/* Action Buttons */}
                        <div style={{ display: "flex", gap: "0.5rem" }}>
                            <button
                                onClick={() => conceptCount > 0 && router.push(`/${grade}/${subject}/${chapter}/${section}/concepts`)}
                                disabled={conceptCount === 0}
                                style={{
                                    display: "flex", alignItems: "center", gap: "0.5rem", padding: "0.75rem 1.25rem",
                                    background: conceptCount > 0 ? "#2e5bff" : "#94a3b8",
                                    color: "white", border: "none", borderRadius: "var(--radius)",
                                    fontWeight: 700, fontSize: "0.875rem",
                                    cursor: conceptCount > 0 ? "pointer" : "not-allowed",
                                    opacity: conceptCount > 0 ? 1 : 0.5,
                                    fontFamily: "var(--font-display)",
                                }}>
                                <span className="material-symbols-outlined" style={{ fontSize: "1.125rem" }}>lightbulb</span>
                                Concepts{conceptCount > 0 ? ` (${conceptCount})` : ""}
                            </button>

                            {/* Test Me */}
                            <button
                                onClick={() => router.push(`/${grade}/${subject}/${chapter}/${section}/test?subsection=${encodeURIComponent(current?.id || "")}`)}
                                style={{
                                    display: "flex", alignItems: "center", gap: "0.5rem", padding: "0.75rem 1.25rem",
                                    background: "#f59e0b", color: "white", border: "none", borderRadius: "var(--radius)",
                                    fontWeight: 700, fontSize: "0.875rem", cursor: "pointer", fontFamily: "var(--font-display)",
                                    boxShadow: "0 4px 12px rgba(245,158,11,0.25)",
                                }}>
                                <span className="material-symbols-outlined" style={{ fontSize: "1.125rem" }}>quiz</span>
                                Test Me
                            </button>

                            {/* MCQ Practice */}
                            <button
                                onClick={() => router.push(`/${grade}/${subject}/${chapter}/${section}/mcq?subsection=${encodeURIComponent(current?.id || "")}`)}
                                style={{
                                    display: "flex", alignItems: "center", gap: "0.5rem", padding: "0.75rem 1.25rem",
                                    background: "#8b5cf6", color: "white", border: "none", borderRadius: "var(--radius)",
                                    fontWeight: 700, fontSize: "0.875rem", cursor: "pointer", fontFamily: "var(--font-display)",
                                    boxShadow: "0 4px 12px rgba(139,92,246,0.25)",
                                }}>
                                <span className="material-symbols-outlined" style={{ fontSize: "1.125rem" }}>check_box</span>
                                MCQ
                            </button>

                            <button
                                onClick={() => router.push(`/${grade}/${subject}/${chapter}/${section}/exercises`)}
                                style={{
                                    display: "flex", alignItems: "center", gap: "0.5rem", padding: "0.75rem 1.25rem",
                                    background: "#ffcc33", color: "#1a1a1a", border: "none", borderRadius: "var(--radius)",
                                    fontWeight: 700, fontSize: "0.875rem", cursor: "pointer", fontFamily: "var(--font-display)",
                                }}>
                                <span className="material-symbols-outlined" style={{ fontSize: "1.125rem" }}>edit_note</span>
                                Chapter End Exercises ({chapterExerciseCount})
                            </button>
                            <button
                                onClick={() => setTutorOpen(true)}
                                style={{
                                display: "flex", alignItems: "center", gap: "0.5rem", padding: "0.75rem 1.25rem",
                                background: "#ff7f50", color: "white", border: "none", borderRadius: "var(--radius)",
                                fontWeight: 700, fontSize: "0.875rem", cursor: "pointer", fontFamily: "var(--font-display)",
                            }}>
                                <span className="material-symbols-outlined" style={{ fontSize: "1.125rem" }}>smart_toy</span>
                                AI Tutor
                            </button>
                        </div>


                        {/* Progress */}
                        <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", color: "var(--text-muted)" }}>
                            <div style={{ height: 6, width: 48, borderRadius: 9999, background: "rgba(20,184,166,0.15)" }}>
                                <div style={{
                                    height: "100%", borderRadius: 9999, background: "var(--primary)",
                                    width: `${((currentIndex + 1) / subsections.length) * 100}%`,
                                    transition: "width 0.3s ease",
                                }} />
                            </div>
                            <span style={{ fontSize: "0.6875rem", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.1em" }}>
                                {currentIndex + 1} of {subsections.length}
                            </span>
                        </div>

                        {/* Nav */}
                        <div style={{ display: "flex", gap: "0.5rem" }}>
                            <button
                                onClick={() => setCurrentIndex((i) => Math.max(0, i - 1))}
                                disabled={currentIndex === 0}
                                style={{
                                    padding: "0.75rem 1.25rem", border: "1px solid var(--border)",
                                    borderRadius: "var(--radius)", background: "white", fontWeight: 700,
                                    fontSize: "0.875rem", cursor: currentIndex === 0 ? "default" : "pointer",
                                    opacity: currentIndex === 0 ? 0.4 : 1, color: "var(--text-secondary)",
                                    fontFamily: "var(--font-display)",
                                }}
                            >
                                Previous
                            </button>
                            <button
                                onClick={() => {
                                    if (currentIndex < subsections.length - 1) {
                                        setCurrentIndex((i) => i + 1);
                                    } else {
                                        // Navigate to the next section in the chapter
                                        const currentSectionIdx = chapterSections.findIndex(
                                            (s) => sectionSlug(s.id) === section
                                        );
                                        if (currentSectionIdx >= 0 && currentSectionIdx < chapterSections.length - 1) {
                                            const nextSlug = sectionSlug(chapterSections[currentSectionIdx + 1].id);
                                            router.push(`/${grade}/${subject}/${chapter}/${nextSlug}`);
                                        } else {
                                            // Last section in chapter — go back to chapter
                                            router.push(`/${grade}/${subject}/${chapter}`);
                                        }
                                    }
                                }}
                                style={{
                                    display: "flex", alignItems: "center", gap: "0.5rem",
                                    padding: "0.75rem 1.5rem", background: "var(--primary)",
                                    color: "#0a2e2b", border: "none", borderRadius: "var(--radius)",
                                    fontWeight: 700, fontSize: "0.875rem", cursor: "pointer",
                                    boxShadow: "0 8px 16px rgba(20,184,166,0.2)", fontFamily: "var(--font-display)",
                                }}
                            >
                                {currentIndex < subsections.length - 1
                                    ? "Next"
                                    : chapterSections.findIndex((s) => sectionSlug(s.id) === section) < chapterSections.length - 1
                                        ? "Next Section"
                                        : "Done"}
                                <span className="material-symbols-outlined" style={{ fontSize: "1.125rem" }}>arrow_forward</span>
                            </button>
                        </div>
                    </div>
                </div>
            </footer>
        </div>
    );
}
