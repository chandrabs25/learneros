"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/lib/auth-context";
import LatexText from "@/components/LatexText";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/* ── Types ─────────────────────────────────────────────────────────── */

interface QuestionData {
    section_id: string;
    section_title: string;
    subsection_id: string;
    question: string;
    hint: string;
    key_terms: string[];
}

interface InsightEntry {
    concept_id: string;
    concept_name: string;
    type: string;
    category: string;
    content: string;
    source_id: string;
}

interface EvalResult {
    score: number;
    grade: string;
    feedback: string;
    strengths: string[];
    improvements: string[];
    model_answer: string;
    insights: InsightEntry[];
    section_id: string;
    persistence_status?: "queued" | "skipped_unauthenticated" | "skipped_invalid_auth" | "skipped_no_insights";
}

/* ── Local Storage helpers ─────────────────────────────────────────── */

const STORAGE_KEY = "ai_tutor_guest_insights";

function loadGuestInsights(): InsightEntry[] {
    if (typeof window === "undefined") return [];
    try {
        const raw = localStorage.getItem(STORAGE_KEY);
        return raw ? JSON.parse(raw) : [];
    } catch {
        return [];
    }
}

function saveGuestInsights(insights: InsightEntry[]) {
    try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(insights));
    } catch { /* quota exceeded — silently ignore */ }
}

/* ── Persist insights ──────────────────────────────────────────────── */

async function persistInsights(
    insights: InsightEntry[],
) {
    if (!insights.length) return;
    // Guest: append to localStorage
    const existing = loadGuestInsights();
    const timestamped = insights.map((ins) => ({
        ...ins,
        created_at: new Date().toISOString(),
    }));
    saveGuestInsights([...existing, ...timestamped]);
}


/* ══════════════════════════════════════════════════════════════════════
   Component
   ══════════════════════════════════════════════════════════════════════ */

export default function TestMePage() {
    const params = useParams();
    const router = useRouter();
    const searchParams = useSearchParams();
    const { user, getIdToken } = useAuth();

    const grade = params.grade as string;
    const subject = params.subject as string;
    const chapter = params.chapter as string;
    const section = params.section as string;

    const sectionId = `ncert:${subject}:${grade}:${chapter}:${section}`;
    const targetSubsection = searchParams.get("subsection") || "";

    const [questionData, setQuestionData] = useState<QuestionData | null>(null);
    const [answer, setAnswer] = useState("");
    const [loading, setLoading] = useState(true);
    const [submitting, setSubmitting] = useState(false);
    const [evalResult, setEvalResult] = useState<EvalResult | null>(null);
    const [error, setError] = useState("");
    const [insightsSaved, setInsightsSaved] = useState(false);
    const [persistenceWarning, setPersistenceWarning] = useState("");

    /* Fetch question on mount */
    useEffect(() => {
        if (!targetSubsection) {
            setError("No subsection specified. Please navigate from a section page.");
            setLoading(false);
            return;
        }
        setLoading(true);
        setError("");
        (async () => {
            try {
                const token = await getIdToken();
                const headers: Record<string, string> = {};
                if (token) headers["Authorization"] = `Bearer ${token}`;
                const r = await fetch(`${API_URL}/api/sections/${sectionId}/test/question?subsection_id=${encodeURIComponent(targetSubsection)}`, { headers });
                if (!r.ok) throw new Error(`HTTP ${r.status}`);
                const data = await r.json();
                setQuestionData(data);
            } catch (e: unknown) {
                setError(e instanceof Error ? e.message : "Failed to generate question");
            } finally {
                setLoading(false);
            }
        })();
    }, [sectionId, getIdToken, targetSubsection]);

    /* Submit answer for evaluation */
    const handleSubmit = async () => {
        if (!answer.trim() || !questionData) return;
        setSubmitting(true);
        setPersistenceWarning("");
        try {
            const token = await getIdToken();
            const headers: Record<string, string> = { "Content-Type": "application/json" };
            if (token) headers["Authorization"] = `Bearer ${token}`;
            const res = await fetch(`${API_URL}/api/sections/${sectionId}/test/evaluate`, {
                method: "POST",
                headers,
                body: JSON.stringify({ question: questionData.question, answer, subsection_id: questionData.subsection_id }),
            });
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const data: EvalResult = await res.json();
            setEvalResult(data);
            setInsightsSaved(false);

            if (data.insights?.length) {
                if (data.persistence_status === "queued") {
                    setInsightsSaved(true);
                } else if (!token) {
                    // Guest users persist locally.
                    persistInsights(data.insights).then(() => setInsightsSaved(true));
                } else if (data.persistence_status === "skipped_invalid_auth") {
                    setPersistenceWarning(
                        "Insights were generated but not saved to backend because the auth token was rejected. Sign out and sign in again."
                    );
                } else if (data.persistence_status === "skipped_unauthenticated") {
                    setPersistenceWarning(
                        "Insights were generated but this request reached backend as unauthenticated, so they were not saved to your profile."
                    );
                }
            }
        } catch (e: unknown) {
            setError(e instanceof Error ? e.message : "Evaluation failed");
        } finally {
            setSubmitting(false);
        }
    };

    /* New question */
    const handleNewQuestion = async () => {
        setEvalResult(null);
        setAnswer("");
        setInsightsSaved(false);
        setPersistenceWarning("");
        setLoading(true);
        setError("");
        try {
            const token = await getIdToken();
            const headers: Record<string, string> = {};
            if (token) headers["Authorization"] = `Bearer ${token}`;
            const r = await fetch(`${API_URL}/api/sections/${sectionId}/test/question?subsection_id=${encodeURIComponent(targetSubsection)}`, { headers });
            const data = await r.json();
            setQuestionData(data);
        } catch {
            setError("Failed to generate question");
        } finally {
            setLoading(false);
        }
    };

    /* Grade colour */
    const gradeColor = (g: string) => {
        if (g === "A") return "#22c55e";
        if (g === "B") return "#14b8a6";
        if (g === "C") return "#f59e0b";
        return "#ef4444";
    };

    /* Insight type label */
    const insightLabel = (type: string) => {
        if (type === "COMPETENCY") return { text: "Understood", color: "#22c55e", icon: "check_circle" };
        if (type === "PARTIAL_UNDERSTANDING") return { text: "Partial", color: "#f59e0b", icon: "help" };
        return { text: "Misconception", color: "#ef4444", icon: "error" };
    };

    return (
        <div className="test-page">
            <div className="test-container">
                {/* Header */}
                <div className="test-header">
                    <nav className="breadcrumb">
                        <Link href="/">Hub</Link>
                        <span className="sep">›</span>
                        <Link href={`/${grade}/${subject}`}>{subject.charAt(0).toUpperCase() + subject.slice(1)}</Link>
                        <span className="sep">›</span>
                        <Link href={`/${grade}/${subject}/${chapter}`}>Chapter {chapter}</Link>
                        <span className="sep">›</span>
                        <Link href={`/${grade}/${subject}/${chapter}/${section}`}>Section {section}</Link>
                        <span className="sep">›</span>
                        <span className="current">Test</span>
                    </nav>

                    <div className="test-badge">
                        <span className="material-symbols-outlined" style={{ fontSize: "0.875rem" }}>psychology</span>
                        Assessment Mode
                    </div>
                    <h1 className="test-title font-display">Testing Your Understanding</h1>
                    <p className="test-subtitle">
                        Take your time to provide a detailed explanation. Our AI will analyze your response for accuracy and depth.
                    </p>
                </div>

                {/* Main layout */}
                <div className="test-layout">
                    {/* Left: Question + Answer */}
                    <div className="test-workspace">
                        {loading ? (
                            <div className="test-loading">
                                <div className="spinner" />
                                <p>Generating your question…</p>
                            </div>
                        ) : error && !questionData ? (
                            <div className="test-error">
                                <span className="material-symbols-outlined">error</span>
                                <p>{error}</p>
                                <button onClick={handleNewQuestion} className="test-retry-btn">Try Again</button>
                            </div>
                        ) : questionData && !evalResult ? (
                            <>
                                {/* Question card */}
                                <div className="test-question-card">
                                    <div className="test-question-progress">
                                        <div className="test-question-progress-fill" />
                                    </div>
                                    <div className="test-question-body">
                                        <div className="test-question-label">
                                            <span className="material-symbols-outlined" style={{ fontSize: "0.875rem", color: "var(--primary)" }}>psychology</span>
                                            <span>AI Generated Question</span>
                                        </div>
                                        <LatexText as="h2" className="test-question-text font-display">{questionData.question}</LatexText>
                                    </div>
                                </div>

                                {/* Answer textarea */}
                                <div className="test-answer-section">
                                    <div className="test-answer-header">
                                        <label className="test-answer-label font-display">Your Detailed Answer</label>
                                        {answer.length > 0 && (
                                            <span className="test-answer-count">{answer.length} characters</span>
                                        )}
                                    </div>
                                    <textarea
                                        className="test-answer-input"
                                        placeholder="Start typing your detailed answer here… Explain the concepts thoroughly and connect key ideas."
                                        value={answer}
                                        onChange={(e) => setAnswer(e.target.value)}
                                        rows={14}
                                    />
                                </div>

                                {/* Actions */}
                                <div className="test-actions">
                                    <button
                                        className="test-cancel-btn"
                                        onClick={() => router.push(`/${grade}/${subject}/${chapter}/${section}`)}
                                    >
                                        <span className="material-symbols-outlined">close</span>
                                        Cancel
                                    </button>
                                    <button
                                        className="test-submit-btn"
                                        onClick={handleSubmit}
                                        disabled={!answer.trim() || submitting}
                                    >
                                        {submitting ? "Evaluating…" : "Submit for AI Evaluation"}
                                        <span className="material-symbols-outlined">{submitting ? "hourglass_top" : "send"}</span>
                                    </button>
                                </div>
                            </>
                        ) : evalResult ? (
                            /* ── Evaluation Results ── */
                            <div className="test-results">
                                <div className="test-results-header">
                                    <div className="test-results-score" style={{ borderColor: gradeColor(evalResult.grade) }}>
                                        <span className="test-results-grade" style={{ color: gradeColor(evalResult.grade) }}>
                                            {evalResult.grade}
                                        </span>
                                        <span className="test-results-number">{evalResult.score}/100</span>
                                    </div>
                                    <div>
                                        <h2 className="test-results-title font-display">Evaluation Complete</h2>
                                        <LatexText as="p" className="test-results-feedback">{evalResult.feedback}</LatexText>
                                    </div>
                                </div>

                                {/* Strengths & Improvements */}
                                <div className="test-results-grid">
                                    {evalResult.strengths?.length > 0 && (
                                        <div className="test-results-card test-results-strengths">
                                            <h4>
                                                <span className="material-symbols-outlined">check_circle</span>
                                                Strengths
                                            </h4>
                                            <ul>
                                                {evalResult.strengths.map((s, i) => <LatexText as="li" key={i}>{s}</LatexText>)}
                                            </ul>
                                        </div>
                                    )}
                                    {evalResult.improvements?.length > 0 && (
                                        <div className="test-results-card test-results-improve">
                                            <h4>
                                                <span className="material-symbols-outlined">trending_up</span>
                                                Areas to Improve
                                            </h4>
                                            <ul>
                                                {evalResult.improvements.map((s, i) => <LatexText as="li" key={i}>{s}</LatexText>)}
                                            </ul>
                                        </div>
                                    )}
                                </div>

                                {/* Concept Insights */}
                                {evalResult.insights?.length > 0 && (
                                    <div className="test-insights-section">
                                        <h3 className="test-insights-title font-display">
                                            <span className="material-symbols-outlined">neurology</span>
                                            Learning Insights
                                            {insightsSaved && (
                                                <span className="test-insights-saved">
                                                    <span className="material-symbols-outlined" style={{ fontSize: "0.75rem" }}>check</span>
                                                    {user ? "Saved to profile" : "Saved locally"}
                                                </span>
                                            )}
                                        </h3>
                                        {persistenceWarning && (
                                            <p className="test-insights-warning">{persistenceWarning}</p>
                                        )}
                                        <div className="test-insights-grid">
                                            {evalResult.insights.map((ins, i) => {
                                                const label = insightLabel(ins.type);
                                                return (
                                                    <div key={i} className="test-insight-chip">
                                                        <div className="test-insight-chip-header">
                                                            <span
                                                                className="material-symbols-outlined"
                                                                style={{ fontSize: "1rem", color: label.color }}
                                                            >
                                                                {label.icon}
                                                            </span>
                                                            <span className="test-insight-concept">{ins.concept_name}</span>
                                                            <span
                                                                className="test-insight-type"
                                                                style={{ color: label.color, borderColor: label.color }}
                                                            >
                                                                {label.text}
                                                            </span>
                                                        </div>
                                                        <LatexText as="p" className="test-insight-content">{ins.content}</LatexText>
                                                    </div>
                                                );
                                            })}
                                        </div>
                                    </div>
                                )}

                                {/* Model answer */}
                                {evalResult.model_answer && (
                                    <div className="test-model-answer">
                                        <h4>
                                            <span className="material-symbols-outlined">auto_awesome</span>
                                            Ideal Answer
                                        </h4>
                                        <p>{evalResult.model_answer}</p>
                                    </div>
                                )}

                                {/* Result actions */}
                                <div className="test-actions">
                                    <button
                                        className="test-cancel-btn"
                                        onClick={() => router.push(`/${grade}/${subject}/${chapter}/${section}`)}
                                    >
                                        <span className="material-symbols-outlined">arrow_back</span>
                                        Back to Section
                                    </button>
                                    <button className="test-submit-btn" onClick={handleNewQuestion}>
                                        Try Another Question
                                        <span className="material-symbols-outlined">refresh</span>
                                    </button>
                                </div>
                            </div>
                        ) : null}
                    </div>

                    {/* Right sidebar */}
                    <aside className="test-sidebar">
                        {/* Context panel */}
                        <div className="test-context-panel">
                            <h3>
                                <span className="material-symbols-outlined">import_contacts</span>
                                Context
                            </h3>
                            <div className="test-context-item">
                                <span className="test-context-label">Subject &amp; Unit</span>
                                <span className="test-context-value">
                                    {subject.charAt(0).toUpperCase() + subject.slice(1)} › Chapter {chapter}
                                </span>
                            </div>
                            <div className="test-context-item">
                                <span className="test-context-label">Section</span>
                                <span className="test-context-value">
                                    {questionData?.section_title || `Section ${section}`}
                                </span>
                            </div>

                            <hr className="test-context-divider" />

                            <h3>
                                <span className="material-symbols-outlined">key</span>
                                Key Terms
                            </h3>
                            <p className="test-context-hint">Include these concepts in your answer for a higher completeness score:</p>
                            <div className="test-terms">
                                {(questionData?.key_terms || []).map((term, i) => (
                                    <span key={i} className="test-term-chip">{term}</span>
                                ))}
                            </div>
                        </div>

                        {/* Pro tip */}
                        <div className="test-pro-tip">
                            <div className="test-pro-tip-bg">
                                <span className="material-symbols-outlined">tips_and_updates</span>
                            </div>
                            <h4>
                                <span className="material-symbols-outlined" style={{ fontSize: "0.875rem" }}>info</span>
                                Pro Tip
                            </h4>
                            <p>{questionData?.hint || "Try explaining the concept as if you were teaching a peer. Using analogies often helps the AI verify your conceptual grasp."}</p>
                        </div>

                        {/* Auth status badge */}
                        <div className="test-auth-badge">
                            <span className="material-symbols-outlined" style={{ fontSize: "1rem" }}>
                                {user ? "cloud_done" : "cloud_off"}
                            </span>
                            <span>
                                {user
                                    ? "Insights saved to your profile"
                                    : "Sign in to save insights to your profile"}
                            </span>
                        </div>
                    </aside>
                </div>
            </div>
        </div>
    );
}
