"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Subject {
    id: string;
    name: string;
    textbook_id: string;
    chapter_count: number;
}

const SUBJECT_CONFIG: Record<string, { icon: string; color: string; tag: string }> = {
    Physics: { icon: "rocket_launch", color: "#8a3ffc", tag: "Modern Science" },
    Chemistry: { icon: "science", color: "#f020b1", tag: "Matter & Energy" },
    Mathematics: { icon: "calculate", color: "#ff3366", tag: "STEM" },
    Biology: { icon: "biotech", color: "#00d166", tag: "Natural Sciences" },
};

const COMING_SOON = [
    { name: "Chemistry", icon: "science", color: "#f020b1", tag: "Matter & Energy" },
    { name: "Mathematics", icon: "calculate", color: "#ff3366", tag: "STEM" },
    { name: "Biology", icon: "biotech", color: "#00d166", tag: "Natural Sciences" },
];

export default function SubjectPage() {
    const params = useParams();
    const grade = params.grade as string;
    const [subjects, setSubjects] = useState<Subject[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetch(`${API_URL}/api/grades/${grade}/subjects`)
            .then((r) => r.json())
            .then((data) => {
                setSubjects(Array.isArray(data) ? data : []);
                setLoading(false);
            })
            .catch(() => setLoading(false));
    }, [grade]);

    if (loading) {
        return (
            <div className="loading-container">
                <div className="spinner" />
                Loading subjects...
            </div>
        );
    }

    return (
        <div className="atlas-page">
            <div className="page-header">
                <nav className="breadcrumb">
                    <Link href="/">Hub</Link>
                    <span className="sep">›</span>
                    <span className="current">Grade {grade}</span>
                </nav>
                <h1 className="font-display">The Atlas</h1>
                <p>A visual map of your learning trajectory. Select a subject to explore its curriculum.</p>
            </div>

            <div className="subject-grid">
                {subjects.map((s) => {
                    const cfg = SUBJECT_CONFIG[s.name] || { icon: "school", color: "#64748b", tag: "Subject" };
                    return (
                        <Link
                            key={s.id}
                            href={`/${grade}/${s.name.toLowerCase()}`}
                            className="subject-card featured"
                        >
                            <div className="card-top">
                                <div className="progress-ring">
                                    <svg viewBox="0 0 36 36" width="48" height="48">
                                        <circle cx="18" cy="18" r="16" fill="none" stroke="#e5e7eb" strokeWidth="3" />
                                        <circle
                                            cx="18" cy="18" r="16" fill="none"
                                            stroke={cfg.color}
                                            strokeWidth="3"
                                            strokeDasharray="5, 100"
                                            strokeLinecap="round"
                                            style={{ transform: "rotate(-90deg)", transformOrigin: "50% 50%" }}
                                        />
                                    </svg>
                                </div>
                            </div>
                            <div className="card-icon" style={{ color: cfg.color }}>
                                <span className="material-symbols-outlined" style={{ fontSize: "4rem" }}>
                                    {cfg.icon}
                                </span>
                            </div>
                            <div className="card-bottom">
                                <h3>{s.name}</h3>
                                <div className="tag">{cfg.tag}</div>
                                <div className="card-meta">
                                    <span>{s.chapter_count} Chapters</span>
                                </div>
                            </div>
                        </Link>
                    );
                })}

                {/* Coming soon placeholders */}
                {COMING_SOON.filter((cs) => !subjects.some((s) => s.name === cs.name)).map((cs) => (
                    <div key={cs.name} className="subject-card coming-soon">
                        <div className="card-top" />
                        <div className="card-icon" style={{ color: cs.color, opacity: 0.4 }}>
                            <span className="material-symbols-outlined" style={{ fontSize: "3.5rem" }}>
                                {cs.icon}
                            </span>
                        </div>
                        <div className="card-bottom">
                            <h3>{cs.name}</h3>
                            <div className="tag">Coming Soon</div>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
}
