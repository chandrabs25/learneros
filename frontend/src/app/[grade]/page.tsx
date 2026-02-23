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
    Economics: { icon: "monitoring", color: "#f59e0b", tag: "Social Sciences" },
    History: { icon: "history_edu", color: "#0ea5e9", tag: "World Cultures" },
    Literature: { icon: "menu_book", color: "#f59e0b", tag: "Arts & Language" },
    Geography: { icon: "public", color: "#0ea5e9", tag: "Social Sciences" },
    "Comp Sci": { icon: "terminal", color: "#4f46e5", tag: "Technology" },
};

const COMING_SOON = [
    { name: "Mathematics", icon: "calculate", color: "#ff3366", tag: "STEM" },
    { name: "Biology", icon: "biotech", color: "#00d166", tag: "Natural Sciences" },
    { name: "History", icon: "history_edu", color: "#0ea5e9", tag: "World Cultures" },
    { name: "Literature", icon: "menu_book", color: "#f59e0b", tag: "Arts & Language" },
    { name: "Geography", icon: "public", color: "#0ea5e9", tag: "Social Sciences" },
    { name: "Comp Sci", icon: "terminal", color: "#4f46e5", tag: "Technology" },
    { name: "Economics", icon: "monitoring", color: "#f59e0b", tag: "Social Sciences" },
];

export default function SubjectPage() {
    const params = useParams();
    const grade = params.grade as string;
    const [subjects, setSubjects] = useState<Subject[]>([]);
    const [loading, setLoading] = useState(true);
    const gradeNum = Number(grade);
    const includeEconomics = gradeNum === 11 || gradeNum === 12;

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
                <div className="header-left-group">
                    <nav className="breadcrumb">
                        <Link href="/">Hub</Link>
                        <span className="sep">›</span>
                        <span className="current">Grade {grade}</span>
                    </nav>
                    <h1 className="font-display">The Atlas</h1>
                    <p>A visual map of your learning trajectory. Select a node to expand the curriculum modules.</p>
                </div>
            </div>

            <div className="subject-grid">
                {subjects.map((s) => {
                    const cfg = SUBJECT_CONFIG[s.name] || { icon: "school", color: "#64748b", tag: "Subject" };
                    const isPhysics = s.name.toLowerCase() === "physics";

                    const pseudoProgress = Math.min((s.name.length * 7) % 100 + 40, 95);

                    return (
                        <Link
                            key={s.id}
                            href={`/${grade}/${s.name.toLowerCase()}`}
                            className={`subject-card ${isPhysics ? 'featured priority' : ''}`}
                        >
                            <div className="card-top">
                                {isPhysics && <div className="tag priority-badge">PRIORITY PATH</div>}
                            </div>

                            {isPhysics ? (
                                <div className="card-image-center">
                                    <div className="featured-image-placeholder">
                                        <div className="orb-ring"></div>
                                        <div className="orb-core"></div>
                                    </div>
                                </div>
                            ) : (
                                <div className="card-icon" style={{ color: cfg.color }}>
                                    <span className="material-symbols-outlined" style={{ fontSize: "4rem" }}>
                                        {cfg.icon}
                                    </span>
                                </div>
                            )}

                            <div className="card-bottom">
                                <h3>{s.name}</h3>
                                {isPhysics ? (
                                    <div className="card-meta">
                                        <span>{s.chapter_count} Chapters</span>
                                    </div>
                                ) : (
                                    <div className="tag">{cfg.tag}</div>
                                )}
                            </div>
                        </Link>
                    );
                })}

                {/* Coming soon placeholders */}
                {COMING_SOON
                    .filter((cs) => (cs.name !== "Economics" ? true : includeEconomics))
                    .filter((cs) => !subjects.some((s) => s.name === cs.name))
                    .map((cs) => {
                        const csProgress = [12, 5, 32, 55, 88][cs.name.length % 5];
                        return (
                            <div key={cs.name} className="subject-card coming-soon">
                                <div className="card-top">
                                    <div className="tag priority-badge" style={{ background: '#f1f5f9', color: '#64748b' }}>COMING SOON</div>
                                </div>
                                <div className="card-icon" style={{ color: cs.color }}>
                                    <span className="material-symbols-outlined" style={{ fontSize: "3.5rem" }}>
                                        {cs.icon}
                                    </span>
                                </div>
                                <div className="card-bottom">
                                    <h3>{cs.name}</h3>
                                    <div className="tag" style={{ color: '#a1a1aa' }}>{cs.tag}</div>
                                </div>
                            </div>
                        );
                    })}
            </div>

            <button className="fab-button">
                <span className="material-symbols-outlined">add</span>
            </button>
        </div>
    );
}
