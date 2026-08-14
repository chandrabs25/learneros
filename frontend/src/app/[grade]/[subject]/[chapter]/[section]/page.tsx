"use client";

import { useEffect, useState, useMemo, useRef } from "react";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/lib/auth-context";
import TutorMarkdown from "@/components/TutorMarkdown";
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

interface TutorMessage {
    role: "user" | "assistant";
    text: string;
    matchedCount?: number;
}

export default function SectionViewerPage() {
    const params = useParams();
    const router = useRouter();
    const searchParams = useSearchParams();
    const grade = params.grade as string;
    const subject = params.subject as string;
    const chapter = params.chapter as string;
    const section = params.section as string;
    const requestedSubsection = searchParams.get("subsection") || "";
    const refreshInsightsRequested = searchParams.get("refreshInsights") === "1";
    const urlAssessmentIds = (searchParams.get("assessmentIds") || "")
        .split(",")
        .map((value) => value.trim())
        .filter(Boolean);
    const { user, getIdToken } = useAuth();

    const [subsections, setSubsections] = useState<Subsection[]>([]);
    const [localAssessmentIds, setLocalAssessmentIds] = useState<string[]>([]);
    const assessmentIds = Array.from(new Set([...urlAssessmentIds, ...localAssessmentIds]));
    const [currentIndex, setCurrentIndex] = useState(0);
    const [loading, setLoading] = useState(true);
    const [contentError, setContentError] = useState("");
    const [conceptCount, setConceptCount] = useState(0);
    const [chapterExerciseCount, setChapterExerciseCount] = useState(0);
    const [chapterSections, setChapterSections] = useState<SectionNavItem[]>([]);
    const [chapterTitle, setChapterTitle] = useState("");
    const [insightsOpen, setInsightsOpen] = useState(false);
    const [insightsLoading, setInsightsLoading] = useState(false);
    const [insightsError, setInsightsError] = useState("");
    const [subsectionInsights, setSubsectionInsights] = useState<SubsectionInsight[]>([]);
    const [subsectionInsightCount, setSubsectionInsightCount] = useState(0);
    const [explainById, setExplainById] = useState<Record<string, ExplainState>>({});
    const [testById, setTestById] = useState<Record<string, TestState>>({});
    const [tutorOpen, setTutorOpen] = useState(false);
    const [tutorSessionId, setTutorSessionId] = useState<string>("");
    const [tutorInput, setTutorInput] = useState("");
    const [tutorSending, setTutorSending] = useState(false);
    const [tutorHistoryLoading, setTutorHistoryLoading] = useState(false);
    const [tutorMessages, setTutorMessages] = useState<TutorMessage[]>([
        { role: "assistant", text: "Ask me anything about this subsection. I will use the section context and your relevant active insights." },
    ]);
    const insightRefreshTimers = useRef<number[]>([]);

    const sectionId = `ncert:${subject}:${grade}:${chapter}:${section}`;
    const chapterId = `ncert:${subject}:${grade}:${chapter}`;

    useEffect(() => {
        fetch(`${API_URL}/api/sections/${sectionId}/subsections`)
            .then(async (r) => {
                const data = await r.json().catch(() => null);
                if (!r.ok) {
                    throw new Error(data?.detail || `Content request failed (${r.status})`);
                }
                return data;
            })
            .then((data) => {
                setSubsections(Array.isArray(data) ? data : []);
                setContentError("");
                setLoading(false);
            })
            .catch((error: unknown) => {
                setSubsections([]);
                setContentError(
                    error instanceof Error ? error.message : "Could not load this section."
                );
                setLoading(false);
            });

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

        const subjectName = subject.charAt(0).toUpperCase() + subject.slice(1);
        fetch(`${API_URL}/api/grades/${grade}/subjects/${subjectName}/chapters`)
            .then((r) => r.json())
            .then((data) => {
                const list = Array.isArray(data) ? data : [];
                const currentChapter = list.find((c) => c?.id === chapterId);
                setChapterTitle(currentChapter?.title || "");
            })
            .catch(() => setChapterTitle(""));
    }, [sectionId, chapterId, grade, subject]);

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

    useEffect(() => {
        if (!requestedSubsection || subsections.length === 0) return;
        const requestedIndex = subsections.findIndex(
            (subsection) => subsection.id === requestedSubsection
        );
        if (requestedIndex >= 0) setCurrentIndex(requestedIndex);
    }, [requestedSubsection, subsections]);

    const loadSubsectionInsights = async (opts?: { silent?: boolean }) => {
        const silent = Boolean(opts?.silent);
        if (!current?.id) return;
        if (!user) {
            setSubsectionInsights([]);
            setSubsectionInsightCount(0);
            if (!silent) {
                setInsightsError("Sign in to view your subsection insights.");
                setInsightsLoading(false);
            }
            return;
        }
        if (!silent) {
            setInsightsLoading(true);
            setInsightsError("");
        }
        try {
            const token = await getIdToken();
            const headers: Record<string, string> = {};
            if (token) headers.Authorization = `Bearer ${token}`;
            const res = await fetch(
                `${API_URL}/api/students/me/insights/subsection/${encodeURIComponent(current.id)}`,
                { headers, cache: "no-store" }
            );
            const data = await res.json();
            if (!res.ok) throw new Error(data?.detail || `HTTP ${res.status}`);
            const parsed = Array.isArray(data) ? data : [];
            setSubsectionInsights(parsed);
            setSubsectionInsightCount(parsed.length);
            const visibleIds = new Set(parsed.map((ins) => ins.id));
            setExplainById((prev) =>
                Object.fromEntries(Object.entries(prev).filter(([id]) => visibleIds.has(id)))
            );
            setTestById((prev) =>
                Object.fromEntries(Object.entries(prev).filter(([id]) => visibleIds.has(id)))
            );
        } catch (e: unknown) {
            setSubsectionInsights([]);
            setSubsectionInsightCount(0);
            if (!silent) {
                setInsightsError(e instanceof Error ? e.message : "Failed to load insights.");
            }
        } finally {
            if (!silent) {
                setInsightsLoading(false);
            }
        }
    };

    const clearScheduledInsightRefreshes = () => {
        insightRefreshTimers.current.forEach((timer) => window.clearTimeout(timer));
        insightRefreshTimers.current = [];
    };

    const scheduleSubsectionInsightRefresh = () => {
        clearScheduledInsightRefreshes();
        insightRefreshTimers.current = [750, 2500, 5500, 9000].map((delay) =>
            window.setTimeout(() => {
                void loadSubsectionInsights({ silent: true });
            }, delay)
        );
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
            if (data.persistence_status === "queued" && data.assessment_id) {
                setLocalAssessmentIds((currentIds) =>
                    currentIds.includes(data.assessment_id)
                        ? currentIds
                        : [...currentIds, data.assessment_id]
                );
            }
            await loadSubsectionInsights();
            scheduleSubsectionInsightRefresh();
        } catch (e: unknown) {
            setTestById((prev) => ({
                ...prev,
                [insightId]: { ...prev[insightId], evaluating: false, error: e instanceof Error ? e.message : "Failed to evaluate." },
            }));
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
                { role: "assistant", text: e instanceof Error ? e.message : "Failed to contact LearnerOS Tutor." },
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
        if (!current?.id) {
            setSubsectionInsightCount(0);
            return;
        }
        loadSubsectionInsights({ silent: true });
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [current?.id, user]);

    useEffect(() => {
        if (
            assessmentIds.length > 0
            && current?.id
            && current.id === requestedSubsection
            && user
        ) {
            let cancelled = false;
            const deadline = Date.now() + 240_000;
            const terminalStatuses = new Set(["COMPLETED", "PARTIAL", "FAILED", "SKIPPED"]);

            const poll = async () => {
                try {
                    const token = await getIdToken();
                    if (!token) throw new Error("Sign in required to refresh saved insights.");
                    const statuses = await Promise.all(
                        assessmentIds.map(async (assessmentId) => {
                            const res = await fetch(
                                `${API_URL}/api/assessment-attempts/${encodeURIComponent(assessmentId)}/status`,
                                { headers: { Authorization: `Bearer ${token}` }, cache: "no-store" }
                            );
                            const data = await res.json();
                            if (!res.ok) {
                                const pollError = new Error(data?.detail || `HTTP ${res.status}`) as Error & {
                                    terminal?: boolean;
                                };
                                pollError.terminal = [401, 403, 404].includes(res.status);
                                throw pollError;
                            }
                            return String(data.insight_status || "");
                        })
                    );
                    if (cancelled) return;
                    if (statuses.every((status) => terminalStatuses.has(status))) {
                        await loadSubsectionInsights({ silent: true });
                        if (statuses.some((status) => status === "FAILED" || status === "PARTIAL")) {
                            setInsightsError("Some learning insights could not be saved. Please try another question.");
                        }
                        return;
                    }
                    if (Date.now() >= deadline) {
                        await loadSubsectionInsights({ silent: true });
                        setInsightsError("Insights are taking longer than expected to update. Please try again shortly.");
                        return;
                    }
                    insightRefreshTimers.current = [window.setTimeout(poll, 1500)];
                } catch (error: unknown) {
                    if (cancelled) return;
                    const terminal = Boolean((error as Error & { terminal?: boolean })?.terminal);
                    if (terminal) {
                        setInsightsError(error instanceof Error ? error.message : "Failed to refresh insights.");
                        return;
                    }
                    if (Date.now() >= deadline) {
                        await loadSubsectionInsights({ silent: true });
                        setInsightsError("Insights are taking longer than expected to update. Please try again shortly.");
                        return;
                    }
                    insightRefreshTimers.current = [window.setTimeout(poll, 1500)];
                }
            };

            void poll();
            return () => {
                cancelled = true;
                clearScheduledInsightRefreshes();
            };
        }
        if (
            refreshInsightsRequested
            && current?.id
            && current.id === requestedSubsection
            && user
        ) {
            scheduleSubsectionInsightRefresh();
        }
        return clearScheduledInsightRefreshes;
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [searchParams, refreshInsightsRequested, requestedSubsection, current?.id, user, localAssessmentIds]);

    useEffect(() => clearScheduledInsightRefreshes, []);

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

    if (contentError) {
        return (
            <div className="loading-container">
                Could not load this section: {contentError}
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
                    <button
                        onClick={() => router.push(`/${grade}/${subject}?chapter=${encodeURIComponent(chapter)}`)}
                        style={{
                            display: "flex",
                            alignItems: "center",
                            gap: "0.4rem",
                            width: "fit-content",
                            padding: "0.5rem 0.875rem",
                            background: "white",
                            border: "1px solid var(--border)",
                            borderRadius: "999px",
                            fontSize: "0.75rem",
                            fontWeight: 700,
                            textTransform: "uppercase",
                            letterSpacing: "0.05em",
                            color: "var(--text-secondary)",
                            cursor: "pointer",
                            boxShadow: "0 2px 5px rgba(0,0,0,0.02)",
                            transition: "all 0.2s ease",
                            marginBottom: "0.9rem",
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
                    <h3 className="section-sidebar-heading">
                        <Link href={`/${grade}/${subject}/${chapter}`} style={{ color: "inherit", textDecoration: "none" }}>
                            {chapterTitle ? `Chapter ${chapter}: ${chapterTitle}` : `Chapter ${chapter}`}
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
                            <Link href="/">Home</Link>
                            <span className="sep">›</span>
                            <Link href={`/${grade}/${subject}`}>
                                {subject.charAt(0).toUpperCase() + subject.slice(1)}
                            </Link>
                            <span className="sep">›</span>
                            <Link href={`/${grade}/${subject}/${chapter}`}>
                                {chapterTitle ? `Chapter ${chapter}: ${chapterTitle}` : `Chapter ${chapter}`}
                            </Link>
                            <span className="sep">›</span>
                            <span className="current">Section {section}</span>
                        </nav>
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
                    <span className="section-insights-tab-label">Insights ({subsectionInsightCount})</span>
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
                                    <div className="section-insight-content">
                                        <TutorMarkdown text={ins.content} compact />
                                    </div>
                                    {(ins.type === "PARTIAL_UNDERSTANDING" || ins.type === "MISCONCEPTION") && (
                                        <div style={{ marginTop: "0.6rem", display: "flex", gap: "0.45rem", flexWrap: "wrap" }}>
                                            <button
                                                onClick={() => runExplain(ins.id)}
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
                                                onClick={() => runTest(ins.id)}
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
                                    )}

                                    {explainById[ins.id] && (
                                        <div style={{ marginTop: "0.55rem", borderRadius: 8, border: "1px solid #bae6fd", background: "#ecfeff", padding: "0.52rem 0.6rem" }}>
                                            {explainById[ins.id].loading ? (
                                                <p style={{ margin: 0, fontSize: "0.78rem", color: "#0f172a" }}>Generating explanation...</p>
                                            ) : explainById[ins.id].error ? (
                                                <p style={{ margin: 0, fontSize: "0.78rem", color: "#b91c1c" }}>{explainById[ins.id].error}</p>
                                            ) : (
                                                <>
                                                    <TutorMarkdown text={explainById[ins.id].text || ""} compact />
                                                    {!!explainById[ins.id].points?.length && (
                                                        <ul style={{ margin: "0.35rem 0 0", paddingLeft: "0.95rem" }}>
                                                            {explainById[ins.id].points!.map((p, i) => (
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

                                    {testById[ins.id] && (
                                        <div style={{ marginTop: "0.55rem", borderRadius: 8, border: "1px solid #bfdbfe", background: "#eff6ff", padding: "0.6rem" }}>
                                            {testById[ins.id].loading ? (
                                                <p style={{ margin: 0, fontSize: "0.78rem", color: "#0f172a" }}>Generating MCQ...</p>
                                            ) : testById[ins.id].error ? (
                                                <p style={{ margin: 0, fontSize: "0.78rem", color: "#b91c1c" }}>{testById[ins.id].error}</p>
                                            ) : (
                                                <>
                                                    <TutorMarkdown text={testById[ins.id].question || ""} compact />
                                                    <div style={{ display: "grid", gap: "0.28rem", marginTop: "0.45rem" }}>
                                                        {Object.entries(testById[ins.id].options || {}).map(([k, v]) => (
                                                            <button
                                                                key={k}
                                                                onClick={() => setTestById((prev) => ({ ...prev, [ins.id]: { ...prev[ins.id], selected: k } }))}
                                                                style={{
                                                                    textAlign: "left",
                                                                    borderRadius: 7,
                                                                    border: `1px solid ${(testById[ins.id].selected === k) ? "#2563eb" : "#cbd5e1"}`,
                                                                    background: (testById[ins.id].selected === k) ? "#dbeafe" : "white",
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
                                                            onClick={() => evaluateTest(ins.id)}
                                                            disabled={!testById[ins.id].selected || !!testById[ins.id].evaluating}
                                                            style={{
                                                                border: "none",
                                                                borderRadius: 7,
                                                                background: "#1d4ed8",
                                                                color: "white",
                                                                fontSize: "0.72rem",
                                                                fontWeight: 800,
                                                                padding: "0.32rem 0.62rem",
                                                                cursor: (!testById[ins.id].selected || !!testById[ins.id].evaluating) ? "not-allowed" : "pointer",
                                                                opacity: (!testById[ins.id].selected || !!testById[ins.id].evaluating) ? 0.6 : 1,
                                                            }}
                                                        >
                                                            {testById[ins.id].evaluating ? "Checking..." : "Submit Test"}
                                                        </button>
                                                        {testById[ins.id].done && (
                                                            <span style={{ fontSize: "0.7rem", color: "#065f46", fontWeight: 700 }}>
                                                                Reconciled and saved.
                                                            </span>
                                                        )}
                                                    </div>
                                                    {!!testById[ins.id].feedback && (
                                                        <div style={{ marginTop: "0.38rem", fontSize: "0.74rem", color: "#1e3a8a" }}>
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
            )}

            {tutorOpen && (
                <div className="section-insights-panel" style={{ right: "20rem", width: "min(32rem, calc(100vw - 2rem))" }}>
                    <div className="section-insights-panel-header">
                        <div>
                            <div className="section-insights-panel-kicker">LearnerOS Tutor</div>
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
                                <TutorMarkdown text={m.text || ""} compact isUser={m.role === "user"} />
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
                            {tutorSending ? <span className="material-symbols-outlined" style={{ fontSize: "1rem", animation: "spin 1s linear infinite" }}>progress_activity</span> : "Send"}
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
                                LearnerOS Tutor
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
