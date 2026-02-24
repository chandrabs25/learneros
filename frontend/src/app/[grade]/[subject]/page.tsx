"use client";

import { useEffect, useState } from "react";
import { useParams, useSearchParams } from "next/navigation";
import Link from "next/link";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Chapter {
    id: string;
    number: number;
    title: string;
    summary: string;
    section_count: number;
    exercise_count: number;
    concept_count: number;
    cover_image_url?: string;
}

export default function ChapterExplorerPage() {
    const params = useParams();
    const searchParams = useSearchParams();
    const grade = params.grade as string;
    const subject = params.subject as string;
    const [chapters, setChapters] = useState<Chapter[]>([]);
    const [selected, setSelected] = useState<Chapter | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const subjectName = subject.charAt(0).toUpperCase() + subject.slice(1);
        const queryChapter = searchParams.get("chapter");
        const storageKey = `learneros:lastChapter:${grade}:${subject}`;
        fetch(`${API_URL}/api/grades/${grade}/subjects/${subjectName}/chapters`)
            .then((r) => r.json())
            .then((data) => {
                const list = Array.isArray(data) ? data : [];
                setChapters(list);
                if (list.length > 0) {
                    const fromQuery = queryChapter
                        ? list.find((ch) => String(ch.number) === String(queryChapter))
                        : null;

                    let fromStorage: Chapter | undefined;
                    if (!fromQuery && typeof window !== "undefined") {
                        const storedChapter = window.localStorage.getItem(storageKey);
                        if (storedChapter) {
                            fromStorage = list.find((ch) => String(ch.number) === String(storedChapter));
                        }
                    }

                    setSelected(fromQuery || fromStorage || list[0]);
                } else {
                    setSelected(null);
                }
                setLoading(false);
            })
            .catch(() => setLoading(false));
    }, [grade, subject, searchParams]);

    useEffect(() => {
        if (!selected) return;
        if (typeof window === "undefined") return;
        const storageKey = `learneros:lastChapter:${grade}:${subject}`;
        window.localStorage.setItem(storageKey, String(selected.number));
    }, [selected, grade, subject]);

    if (loading) {
        return (
            <div className="loading-container">
                <div className="spinner" />
                Loading chapters...
            </div>
        );
    }

    return (
        <div className="deep-dive-page">
            {/* ── Sidebar: Chapter List ── */}
            <aside className="chapter-sidebar">
                <div className="sidebar-header">
                    <Link href={`/${grade}`} className="back-btn">
                        <span className="material-symbols-outlined" style={{ fontSize: "0.875rem" }}>
                            arrow_back
                        </span>
                        Back to Subjects
                    </Link>
                    <div className="subject-title">
                        <div>
                            <div style={{ fontSize: "0.6875rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.15em", marginBottom: "0.25rem" }}>
                                Subject
                            </div>
                            <h1>{subject.charAt(0).toUpperCase() + subject.slice(1)}</h1>
                        </div>
                        <span className="count">{chapters.length} Chapters</span>
                    </div>
                </div>

                <div className="chapter-list">
                    {chapters.map((ch) => (
                        <div
                            key={ch.id}
                            className={`chapter-item ${selected?.id === ch.id ? "active" : ""}`}
                            onClick={() => setSelected(ch)}
                        >
                            <div className="chapter-num">
                                Chapter {String(ch.number).padStart(2, "0")}
                            </div>
                            <div className="chapter-title">{ch.title}</div>
                            <div className="chapter-meta">
                                <span>{ch.section_count} Sections</span>
                                <span className="dot" />
                                <span>{ch.exercise_count} Exercises</span>
                            </div>
                        </div>
                    ))}
                </div>
            </aside>

            {/* ── Detail Panel ── */}
            <section className="chapter-detail">
                {selected ? (
                    <>
                        <div
                            className="hero-area"
                            style={{
                                backgroundImage: selected.cover_image_url
                                    ? `url("${selected.cover_image_url}")`
                                    : undefined,
                                backgroundSize: selected.cover_image_url ? "cover" : undefined,
                                backgroundPosition: selected.cover_image_url ? "center" : undefined,
                            }}
                        >
                            <div className="badges">
                                <span className="badge badge-dark">Grade {grade}</span>
                                <span className="badge badge-light">
                                    {subject.charAt(0).toUpperCase() + subject.slice(1)}
                                </span>
                            </div>
                        </div>
                        <div className="detail-content">
                            <h1>{selected.title}</h1>
                            <div className="chapter-subtitle">
                                Chapter {selected.number} · {subject.charAt(0).toUpperCase() + subject.slice(1)}
                            </div>

                            <div className="glass-panel">
                                <div className="panel-grid">
                                    <div className="panel-summary">
                                        <div className="label">Chapter Overview</div>
                                        <p>
                                            {(() => {
                                                const text = selected.summary || `Explore the core concepts and problem-solving techniques in ${selected.title}.`;
                                                return text.length > 300 ? text.slice(0, 300).trimEnd() + "…" : text;
                                            })()}
                                        </p>
                                    </div>
                                    <div className="panel-stats">
                                        <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem", marginBottom: "1.5rem" }}>
                                            <div className="stat-row">
                                                <span className="stat-label">Sections</span>
                                                <span className="stat-value">{selected.section_count}</span>
                                            </div>
                                            <div className="stat-row">
                                                <span className="stat-label">Exercises</span>
                                                <span className="stat-value">{selected.exercise_count}</span>
                                            </div>
                                            <div className="stat-row">
                                                <span className="stat-label">Concepts</span>
                                                <span className="stat-value">{selected.concept_count}</span>
                                            </div>
                                        </div>
                                        <Link
                                            href={`/${grade}/${subject}/${selected.number}`}
                                            className="start-btn"
                                        >
                                            <span className="material-symbols-outlined">play_arrow</span>
                                            Explore Chapter
                                        </Link>
                                        <Link
                                            href={`/${grade}/${subject}/${selected.number}/graph`}
                                            className="start-btn"
                                            style={{
                                                background: "#0a0a0a",
                                                color: "white",
                                                marginTop: "0.5rem",
                                            }}
                                        >
                                            <span className="material-symbols-outlined">hub</span>
                                            Knowledge Graph
                                        </Link>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </>
                ) : (
                    <div className="loading-container">Select a chapter</div>
                )}
            </section>
        </div>
    );
}
