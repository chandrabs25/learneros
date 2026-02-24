"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/lib/auth-context";
import LatexText from "@/components/LatexText";
import { fetchGenerationJSON } from "@/lib/generation-cache";
import TutorMarkdown from "@/components/TutorMarkdown";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface SectionConcept {
    id: string;
}

interface MCQData {
    question: string;
    options: Record<string, string>;
    correct_answer: string;
    explanation: string;
    subsection_id: string;
    key_terms: string[];
}

interface MCQResult {
    is_correct: boolean;
    selected: string;
    correct_answer: string;
    feedback: string;
    explanation: string;
    persistence_status?: "queued" | "skipped_unauthenticated" | "skipped_invalid_auth" | "skipped_no_insights";
    insights: Array<{
        concept_id: string;
        concept_name: string;
        type: string;
        category: string;
        content: string;
        source_id: string;
    }>;
}

const STORAGE_KEY = "ai_tutor_guest_insights";

function loadGuestInsights() {
    if (typeof window === "undefined") return [];
    try {
        const raw = localStorage.getItem(STORAGE_KEY);
        return raw ? JSON.parse(raw) : [];
    } catch {
        return [];
    }
}

function saveGuestInsights(insights: unknown[]) {
    try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(insights));
    } catch {
        // Ignore local storage write failures.
    }
}

export default function MCQPracticePage() {
    const params = useParams();
    const router = useRouter();
    const searchParams = useSearchParams();
    const { getIdToken } = useAuth();
    const grade = params.grade as string;
    const subject = params.subject as string;
    const chapter = params.chapter as string;
    const section = params.section as string;
    const targetSubsection = searchParams.get("subsection") || "";

    const sectionId = `ncert:${subject}:${grade}:${chapter}:${section}`;

    const [questionIndex, setQuestionIndex] = useState(0);
    const [questionPlan, setQuestionPlan] = useState<Array<string | null>>([]);
    const [mcq, setMcq] = useState<MCQData | null>(null);
    const [loading, setLoading] = useState(true);
    const [selected, setSelected] = useState<string | null>(null);
    const [result, setResult] = useState<MCQResult | null>(null);
    const [submitting, setSubmitting] = useState(false);
    const [score, setScore] = useState({ correct: 0, total: 0 });
    const [allInsights, setAllInsights] = useState<MCQResult["insights"]>([]);
    const [persistenceMessage, setPersistenceMessage] = useState("");
    const [error, setError] = useState("");
    const totalQuestions = questionPlan.length || 2;

    // Fetch a new MCQ question
    const fetchQuestion = useCallback(async () => {
        if (!targetSubsection) {
            setError("No subsection specified. Please navigate from a section page.");
            setLoading(false);
            return;
        }
        setLoading(true);
        setError("");
        setSelected(null);
        setResult(null);
        try {
            const targetConceptId = questionPlan[questionIndex];
            const conceptPart = targetConceptId ? `&concept_id=${encodeURIComponent(targetConceptId)}` : "";
            const data = await fetchGenerationJSON<MCQData>(
                `${API_URL}/api/sections/${sectionId}/test/mcq?subsection_id=${encodeURIComponent(targetSubsection)}${conceptPart}&variant=${questionIndex}`
            );
            setMcq(data);
        } catch (e: unknown) {
            setError(e instanceof Error ? e.message : "Failed to load question");
            setMcq(null);
        }
        setLoading(false);
    }, [sectionId, targetSubsection, questionPlan, questionIndex]);

    // Build question plan: minimum 2 questions, else one per concept.
    useEffect(() => {
        if (!targetSubsection) {
            setError("No subsection specified. Please navigate from a section page.");
            setLoading(false);
            setQuestionPlan([]);
            return;
        }
        (async () => {
            try {
                const res = await fetch(`${API_URL}/api/sections/${sectionId}/concepts`);
                const data = await res.json();
                const conceptIds = Array.isArray(data)
                    ? Array.from(new Set((data as SectionConcept[]).map((c) => c.id).filter(Boolean)))
                    : [];

                if (conceptIds.length === 0) {
                    setQuestionPlan([null, null]);
                } else if (conceptIds.length === 1) {
                    setQuestionPlan([conceptIds[0], conceptIds[0]]);
                } else {
                    setQuestionPlan(conceptIds);
                }
                setQuestionIndex(0);
            } catch {
                setQuestionPlan([null, null]);
                setQuestionIndex(0);
            }
        })();
    }, [sectionId, targetSubsection]);

    useEffect(() => {
        if (questionPlan.length === 0) return;
        fetchQuestion();
    }, [questionPlan, questionIndex, fetchQuestion]);

    // Submit answer
    const handleSubmit = async () => {
        if (!selected || !mcq) return;
        setSubmitting(true);
        setPersistenceMessage("");
        try {
            const token = await getIdToken();
            const headers: Record<string, string> = { "Content-Type": "application/json" };
            if (token) headers["Authorization"] = `Bearer ${token}`;
            const res = await fetch(`${API_URL}/api/sections/${sectionId}/test/mcq/evaluate`, {
                method: "POST",
                headers,
                body: JSON.stringify({
                    question: mcq.question,
                    options: mcq.options,
                    selected,
                    correct_answer: mcq.correct_answer,
                    subsection_id: mcq.subsection_id,
                }),
            });
            const data: MCQResult = await res.json();
            setResult(data);
            setScore((s) => ({
                correct: s.correct + (data.is_correct ? 1 : 0),
                total: s.total + 1,
            }));
            if (data.insights?.length) {
                setAllInsights((prev) => [...prev, ...data.insights]);
                if (data.persistence_status === "queued") {
                    setPersistenceMessage("Insights saved to your profile.");
                } else if (!token) {
                    const existing = loadGuestInsights();
                    const timestamped = data.insights.map((ins) => ({
                        ...ins,
                        created_at: new Date().toISOString(),
                    }));
                    saveGuestInsights([...existing, ...timestamped]);
                    setPersistenceMessage("Insights saved locally. Sign in to sync to your profile.");
                } else if (data.persistence_status === "skipped_invalid_auth") {
                    setPersistenceMessage(
                        "Insights were generated but backend rejected your auth token, so they were not saved."
                    );
                } else if (data.persistence_status === "skipped_unauthenticated") {
                    setPersistenceMessage(
                        "Insights were generated but this request reached backend as unauthenticated."
                    );
                }
            }
        } catch {
            /* ignore */
        }
        setSubmitting(false);
    };

    // Next question
    const handleNext = () => {
        if (questionIndex >= totalQuestions - 1) {
            router.push(`/${grade}/${subject}/${chapter}/${section}`);
            return;
        }
        setQuestionIndex((i) => i + 1);
    };

    const progressPct = Math.round(((questionIndex + (result ? 1 : 0)) / totalQuestions) * 100);
    const optionLabels = ["A", "B", "C", "D"];

    return (
        <div className="mcq-page">
            {/* Header */}
            <header className="mcq-header">
                <div className="mcq-header-left">
                    <div className="mcq-header-icon">
                        <span className="material-symbols-outlined">auto_stories</span>
                    </div>
                    <div>
                        <h1 className="mcq-header-title">The Practice</h1>
                        <p className="mcq-header-subtitle">Section {section} · MCQ</p>
                    </div>
                </div>
                <Link
                    href={`/${grade}/${subject}/${chapter}/${section}`}
                    className="mcq-back-btn"
                >
                    <span className="material-symbols-outlined" style={{ fontSize: "1rem" }}>arrow_back</span>
                    Back to Lesson
                </Link>
            </header>

            <main className="mcq-main">
                {/* Progress bar */}
                <div className="mcq-progress-area">
                    <div className="mcq-progress-meta">
                        <span>Question {questionIndex + 1} of {totalQuestions}</span>
                        <span className="mcq-progress-pct">{progressPct}% Complete</span>
                    </div>
                    <div className="mcq-progress-track">
                        {Array.from({ length: totalQuestions }).map((_, i) => (
                            <div
                                key={i}
                                className={`mcq-progress-step ${i < questionIndex || (i === questionIndex && result)
                                    ? "mcq-progress-step--done"
                                    : i === questionIndex
                                        ? "mcq-progress-step--active"
                                        : ""
                                    }`}
                            />
                        ))}
                    </div>
                </div>

                {/* Question card */}
                <div className="mcq-card">
                    {loading ? (
                        <div className="mcq-loading">
                            <div className="spinner" />
                            <p>Generating question...</p>
                        </div>
                    ) : error ? (
                        <p>{error}</p>
                    ) : mcq ? (
                        <>
                            <div className="mcq-card-badge">MULTIPLE CHOICE</div>
                            <div className="mcq-question">
                                <TutorMarkdown text={mcq.question} />
                            </div>

                            {/* Options */}
                            <div className="mcq-options">
                                {optionLabels.map((label) => {
                                    const text = mcq.options[label];
                                    if (!text) return null;
                                    const isSelected = selected === label;
                                    const isCorrect = result && label === result.correct_answer;
                                    const isWrong = result && isSelected && !result.is_correct;

                                    let cls = "mcq-option";
                                    if (result) {
                                        if (isCorrect) cls += " mcq-option--correct";
                                        else if (isWrong) cls += " mcq-option--wrong";
                                        else cls += " mcq-option--disabled";
                                    } else if (isSelected) {
                                        cls += " mcq-option--selected";
                                    }

                                    return (
                                        <button
                                            key={label}
                                            className={cls}
                                            onClick={() => !result && setSelected(label)}
                                            disabled={!!result}
                                        >
                                            <span className="mcq-option-label">{label}</span>
                                            <div className="mcq-option-text">
                                                <TutorMarkdown text={text} compact />
                                            </div>
                                            {result && isCorrect && (
                                                <span className="material-symbols-outlined mcq-option-icon">check_circle</span>
                                            )}
                                            {result && isWrong && (
                                                <span className="material-symbols-outlined mcq-option-icon">cancel</span>
                                            )}
                                        </button>
                                    );
                                })}
                            </div>

                            {/* Result feedback */}
                            {result && (
                                <div className={`mcq-feedback ${result.is_correct ? "mcq-feedback--correct" : "mcq-feedback--wrong"}`}>
                                    <div className="mcq-feedback-header">
                                        <span className="material-symbols-outlined">
                                            {result.is_correct ? "emoji_events" : "info"}
                                        </span>
                                        <strong>{result.is_correct ? "Correct!" : "Not quite right"}</strong>
                                    </div>
                                    <TutorMarkdown text={result.feedback} compact />
                                    {result.explanation && (
                                        <div className="mcq-feedback-explanation">
                                            <TutorMarkdown text={result.explanation} compact />
                                        </div>
                                    )}
                                </div>
                            )}

                            {/* Insight details */}
                            {result && result.insights && result.insights.length > 0 && (
                                <div className="mcq-insights">
                                    <div className="mcq-insights-header">
                                        <span className="material-symbols-outlined" style={{ fontSize: "1.125rem" }}>neurology</span>
                                        <strong>Learning Insights</strong>
                                    </div>
                                    {persistenceMessage && (
                                        <p className="mcq-persistence-message">{persistenceMessage}</p>
                                    )}
                                    {result.insights.map((ins, idx) => {
                                        const typeColors: Record<string, { bg: string; text: string; label: string }> = {
                                            COMPETENCY: { bg: "#dcfce7", text: "#15803d", label: "Competency" },
                                            MISCONCEPTION: { bg: "#fee2e2", text: "#b91c1c", label: "Misconception" },
                                            PARTIAL_UNDERSTANDING: { bg: "#fef3c7", text: "#92400e", label: "Partial Understanding" },
                                        };
                                        const style = typeColors[ins.type] || { bg: "#f3f4f6", text: "#374151", label: ins.type };
                                        return (
                                            <div key={idx} className="mcq-insight-card">
                                                <div className="mcq-insight-top">
                                                    <span className="mcq-insight-concept">{ins.concept_name}</span>
                                                    <span
                                                        className="mcq-insight-badge"
                                                        style={{ background: style.bg, color: style.text }}
                                                    >
                                                        {style.label}
                                                    </span>
                                                </div>
                                                <LatexText as="p" className="mcq-insight-content">{ins.content}</LatexText>
                                            </div>
                                        );
                                    })}
                                </div>
                            )}

                            {/* Actions */}
                            <div className="mcq-actions">
                                {!result ? (
                                    <>
                                        <button
                                            className="mcq-skip-btn"
                                            onClick={handleNext}
                                        >
                                            Skip
                                        </button>
                                        <button
                                            className="mcq-submit-btn"
                                            onClick={handleSubmit}
                                            disabled={!selected || submitting}
                                        >
                                            {submitting ? "Evaluating..." : "Submit Answer"}
                                            <span className="material-symbols-outlined" style={{ fontSize: "1.125rem" }}>send</span>
                                        </button>
                                    </>
                                ) : (
                                    <button className="mcq-next-btn" onClick={handleNext}>
                                        {questionIndex >= totalQuestions - 1 ? "Finish" : "Next Question"}
                                        <span className="material-symbols-outlined" style={{ fontSize: "1.125rem" }}>arrow_forward</span>
                                    </button>
                                )}
                            </div>
                        </>
                    ) : (
                        <p>Failed to load question. Please go back and try again.</p>
                    )}
                </div>

                {/* Score summary (bottom) */}
                {score.total > 0 && (
                    <div className="mcq-score-bar">
                        <span className="material-symbols-outlined" style={{ fontSize: "1rem" }}>stars</span>
                        <span>{score.correct} / {score.total} correct</span>
                        {allInsights.length > 0 && (
                            <span className="mcq-score-insights">
                                · {allInsights.length} insight{allInsights.length > 1 ? "s" : ""} captured
                            </span>
                        )}
                    </div>
                )}
            </main>
        </div>
    );
}
