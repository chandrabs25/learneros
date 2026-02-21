"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import LatexText from "@/components/LatexText";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Concept {
    id: string;
    name: string;
    concept_key: string;
    has_animation: boolean;
    animation_url: string | null;
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
}

/* ── insight type → colour ── */
const insightColor = (type: string) => {
    switch (type) {
        case "COMPETENCY": return "#22c55e";
        case "MISCONCEPTION": return "#ef4444";
        case "PARTIAL_UNDERSTANDING": return "#f59e0b";
        case "TAUGHT": return "#2e5bff";
        default: return "#94a3b8";
    }
};
const insightIcon = (type: string) => {
    switch (type) {
        case "COMPETENCY": return "check_circle";
        case "MISCONCEPTION": return "error";
        case "PARTIAL_UNDERSTANDING": return "help";
        case "TAUGHT": return "school";
        default: return "circle";
    }
};

const C = {
    primary: "#13ecda",
    coral: "#ff6b6b",
    blue: "#2e5bff",
    offWhite: "#fcfcf9",
    dark: "#1a1a1a",
    white: "#ffffff",
};

export default function ConceptsPage() {
    const params = useParams();
    const router = useRouter();
    const { getIdToken } = useAuth();
    const grade = params.grade as string;
    const subject = params.subject as string;
    const chapter = params.chapter as string;
    const section = params.section as string;
    const sectionId = `ncert:${subject}:${grade}:${chapter}:${section}`;

    const [concepts, setConcepts] = useState<Concept[]>([]);
    const [selectedIdx, setSelectedIdx] = useState(0);
    const [loading, setLoading] = useState(true);
    const [sectionTitle, setSectionTitle] = useState("");
    const [showInsights, setShowInsights] = useState(false);
    const [insights, setInsights] = useState<InsightItem[]>([]);
    const [insightsLoading, setInsightsLoading] = useState(false);

    useEffect(() => {
        fetch(`${API_URL}/api/sections/${sectionId}/concepts`)
            .then((r) => r.json())
            .then((data: Concept[]) => {
                setConcepts(data.filter((c) => c.has_animation));
                setLoading(false);
            })
            .catch(() => setLoading(false));

        fetch(`${API_URL}/api/sections/${sectionId}/subsections`)
            .then((r) => r.json())
            .then((data) => {
                if (Array.isArray(data) && data.length > 0) {
                    setSectionTitle(data[0].title || "");
                }
            })
            .catch(() => { });

        // Fetch student insights for this chapter
        const chapterId = `ncert:${subject}:${grade}:${chapter}`;
        setInsightsLoading(true);
        (async () => {
            try {
                const token = await getIdToken();
                const headers: Record<string, string> = {};
                if (token) headers["Authorization"] = `Bearer ${token}`;
                const r = await fetch(`${API_URL}/api/students/me/insights?chapter_id=${chapterId}`, { headers });
                if (!r.ok) throw new Error();
                const data = await r.json();
                setInsights(Array.isArray(data) ? data : []);
            } catch {
                setInsights([]);
            } finally {
                setInsightsLoading(false);
            }
        })();
    }, [sectionId, subject, grade, chapter, getIdToken]);

    const selected = concepts[selectedIdx] ?? null;
    const animationSrc = selected
        ? `${API_URL}${selected.animation_url}?v=${Date.now()}`
        : null;

    /* ── Loading state ── */
    if (loading) {
        return (
            <div style={{
                minHeight: "100vh", display: "flex", alignItems: "center",
                justifyContent: "center", background: C.offWhite,
                fontFamily: "'Space Grotesk', sans-serif", color: C.dark,
            }}>
                <div style={{ textAlign: "center" }}>
                    <span className="material-symbols-outlined" style={{ fontSize: 36, color: C.blue, animation: "spin 1s linear infinite" }}>progress_activity</span>
                    <p style={{ marginTop: 16, opacity: 0.6, fontWeight: 500 }}>Loading concept lab…</p>
                </div>
            </div>
        );
    }

    return (
        <>
            {/* Global page styles – no CDN dependency */}
            <style dangerouslySetInnerHTML={{
                __html: `
                @keyframes spin { to { transform: rotate(360deg); } }
                @keyframes pulse { 0%,100% { opacity:1 } 50% { opacity:0.5 } }
                .concepts-scrollbar::-webkit-scrollbar { width: 3px; }
                .concepts-scrollbar::-webkit-scrollbar-track { background: transparent; }
                .concepts-scrollbar::-webkit-scrollbar-thumb { background: rgba(0,0,0,0.1); border-radius: 10px; }
            `}} />

            <div style={{
                color: C.dark, height: "100vh", display: "flex", flexDirection: "column",
                overflow: "hidden", position: "relative",
                fontFamily: "'Space Grotesk', sans-serif", background: C.offWhite,
            }}>
                {/* ── HEADER ── */}
                <header style={{
                    flexShrink: 0, zIndex: 60, background: C.offWhite,
                    borderBottom: "1px solid rgba(0,0,0,0.05)",
                }}>
                    {/* Top row: back / title / insights */}
                    <div style={{
                        display: "flex", alignItems: "center",
                        padding: "16px 40px",
                    }}>
                        {/* Back button (Left) */}
                        <div style={{ flex: 1, display: "flex", justifyContent: "flex-start" }}>
                            <button
                                onClick={() => router.push(`/${grade}/${subject}/${chapter}/${section}`)}
                                style={{
                                    display: "flex", alignItems: "center", gap: 8,
                                    color: "rgba(26,26,26,0.6)", background: "none", border: "none",
                                    cursor: "pointer", fontFamily: "inherit", transition: "color 0.2s",
                                }}
                                onMouseEnter={e => (e.currentTarget.style.color = C.dark)}
                                onMouseLeave={e => (e.currentTarget.style.color = "rgba(26,26,26,0.6)")}
                            >
                                <span className="material-symbols-outlined" style={{ fontSize: 20 }}>arrow_back</span>
                                <span style={{ fontSize: 11, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.1em" }}>Back</span>
                            </button>
                        </div>

                        {/* Section title (Center) */}
                        <div style={{ flex: 2, display: "flex", justifyContent: "center" }}>
                            <h2 style={{
                                fontSize: 13, fontWeight: 700, letterSpacing: "0.12em",
                                textTransform: "uppercase", maxWidth: 480, overflow: "hidden",
                                textOverflow: "ellipsis", whiteSpace: "nowrap", margin: 0,
                                textAlign: "center",
                            }}>
                                {sectionTitle || `Section ${section}`}
                                <span style={{ color: "rgba(26,26,26,0.3)", margin: "0 8px" }}>//</span>
                                Concept Lab
                            </h2>
                        </div>

                        {/* Spacer (Right) to balance the flex container */}
                        <div style={{ flex: 1 }}></div>
                    </div>

                    {/* Bottom row: concept selector pills */}
                    {concepts.length > 0 && (
                        <div style={{
                            display: "flex", alignItems: "center", gap: 6,
                            padding: "0 40px 14px 40px",
                            overflowX: "auto",
                        }} className="concepts-scrollbar">
                            {concepts.map((c, i) => (
                                <button
                                    key={c.id}
                                    onClick={() => setSelectedIdx(i)}
                                    style={{
                                        padding: "8px 16px", borderRadius: 999, fontSize: 10,
                                        fontWeight: 700, textTransform: "uppercase",
                                        letterSpacing: "0.08em", whiteSpace: "nowrap",
                                        border: i === selectedIdx ? "none" : "1px solid rgba(0,0,0,0.1)",
                                        cursor: "pointer", fontFamily: "inherit",
                                        transition: "all 0.2s",
                                        background: i === selectedIdx ? C.dark : "transparent",
                                        color: i === selectedIdx ? C.white : "rgba(26,26,26,0.5)",
                                        boxShadow: i === selectedIdx ? "0 2px 6px rgba(0,0,0,0.12)" : "none",
                                    }}
                                >
                                    {c.name}
                                </button>
                            ))}
                        </div>
                    )}
                </header>

                {/* ── MAIN – animation area ── */}
                <main style={{
                    position: "relative", flexGrow: 1, display: "flex",
                    alignItems: "center", justifyContent: "center", overflow: "hidden",
                }}>
                    {concepts.length === 0 ? (
                        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", height: "100%", zIndex: 10 }}>
                            <span className="material-symbols-outlined" style={{ fontSize: 64, opacity: 0.2, marginBottom: 16 }}>science</span>
                            <p style={{ fontWeight: 700, fontSize: 18, margin: 0 }}>No concept animations</p>
                            <p style={{ fontSize: 14, color: "rgba(26,26,26,0.5)", textAlign: "center", maxWidth: 400, marginTop: 8 }}>
                                Interactive 3D animations will appear here when available for the concepts covered in this lesson.
                            </p>
                        </div>
                    ) : animationSrc ? (
                        <iframe
                            key={animationSrc}
                            src={animationSrc}
                            title={selected?.name || "Concept Animation"}
                            style={{ position: "absolute", inset: 0, width: "100%", height: "100%", border: "none", pointerEvents: "auto" }}
                            allow="accelerometer; gyroscope"
                            sandbox="allow-scripts allow-same-origin"
                        />
                    ) : (
                        <div style={{ position: "relative", width: 700, height: 450, opacity: 0.4, pointerEvents: "none" }}>
                            <svg style={{ position: "absolute", inset: 0, width: "100%", height: "100%" }} viewBox="0 0 700 450">
                                <path d="M 50 400 Q 350 50 650 400" fill="none" stroke="currentColor" strokeDasharray="10 5" strokeWidth="1.5" />
                                <circle cx="50" cy="400" fill={C.blue} r="8" />
                                <line stroke="currentColor" strokeWidth="0.5" x1="0" x2="700" y1="400" y2="400" />
                            </svg>
                        </div>
                    )}

                    {/* ── AI Insights Popup Modal ── */}
                    {showInsights && (
                        <div
                            onClick={() => setShowInsights(false)}
                            style={{
                                position: "absolute", inset: 0, zIndex: 70,
                                display: "flex", alignItems: "center", justifyContent: "center",
                                background: "rgba(26,26,26,0.2)", backdropFilter: "blur(6px)",
                                padding: 16, pointerEvents: "auto",
                            }}
                        >
                            <div
                                onClick={e => e.stopPropagation()}
                                style={{
                                    background: "rgba(252,252,249,0.97)", backdropFilter: "blur(8px)",
                                    border: "1px solid rgba(0,0,0,0.06)", borderRadius: 20,
                                    padding: 28, display: "flex", flexDirection: "column",
                                    width: "100%", maxWidth: 400, maxHeight: "80vh",
                                    boxShadow: "0 12px 40px -10px rgba(0,0,0,0.12)",
                                }}
                            >
                                {/* Modal header */}
                                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 24 }}>
                                    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                                        <span className="material-symbols-outlined" style={{ fontSize: 24, color: C.primary }}>insights</span>
                                        <h3 style={{ margin: 0, fontSize: 14, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.08em" }}>AI Insights</h3>
                                        <div style={{ width: 8, height: 8, borderRadius: "50%", background: C.primary, animation: "pulse 2s infinite", marginLeft: 4 }} />
                                    </div>
                                    <button
                                        onClick={() => setShowInsights(false)}
                                        style={{ background: "none", border: "none", cursor: "pointer", color: "rgba(26,26,26,0.4)", padding: 4, display: "flex" }}
                                    >
                                        <span className="material-symbols-outlined" style={{ fontSize: 20 }}>close</span>
                                    </button>
                                </div>

                                {/* Modal body */}
                                <div className="concepts-scrollbar" style={{ overflowY: "auto", paddingRight: 8 }}>
                                    {insightsLoading ? (
                                        <div style={{ textAlign: "center", padding: "32px 0" }}>
                                            <span className="material-symbols-outlined" style={{ fontSize: 28, color: C.blue, animation: "spin 1s linear infinite" }}>progress_activity</span>
                                            <p style={{ margin: "12px 0 0", fontSize: 13, color: "rgba(26,26,26,0.5)", fontWeight: 500 }}>Loading insights…</p>
                                        </div>
                                    ) : insights.length === 0 ? (
                                        <div style={{ textAlign: "center", padding: "32px 0" }}>
                                            <span className="material-symbols-outlined" style={{ fontSize: 40, color: "rgba(26,26,26,0.15)" }}>psychology</span>
                                            <p style={{ margin: "12px 0 4px", fontSize: 14, fontWeight: 700, color: "rgba(26,26,26,0.6)" }}>No insights yet</p>
                                            <p style={{ margin: 0, fontSize: 13, color: "rgba(26,26,26,0.4)", lineHeight: 1.5 }}>
                                                Complete exercises and interact with the AI Tutor to build your learning profile.
                                            </p>
                                        </div>
                                    ) : (
                                        <>
                                            {/* Stats summary */}
                                            <div style={{ display: "flex", gap: 8, marginBottom: 20 }}>
                                                {["COMPETENCY", "MISCONCEPTION", "PARTIAL_UNDERSTANDING"].map(t => {
                                                    const count = insights.filter(i => i.type === t).length;
                                                    if (count === 0) return null;
                                                    return (
                                                        <div key={t} style={{
                                                            display: "flex", alignItems: "center", gap: 6,
                                                            background: `${insightColor(t)}12`, border: `1px solid ${insightColor(t)}30`,
                                                            borderRadius: 999, padding: "4px 10px",
                                                        }}>
                                                            <div style={{ width: 6, height: 6, borderRadius: "50%", background: insightColor(t) }} />
                                                            <span style={{ fontSize: 10, fontWeight: 700, color: insightColor(t) }}>{count}</span>
                                                        </div>
                                                    );
                                                })}
                                            </div>

                                            {/* Insights list */}
                                            <ul style={{ listStyle: "none", margin: 0, padding: 0, display: "flex", flexDirection: "column", gap: 12 }}>
                                                {insights.map((ins, idx) => (
                                                    <li key={ins.id || idx} style={{
                                                        display: "flex", gap: 12, padding: "12px 14px",
                                                        background: "rgba(26,26,26,0.02)", borderRadius: 12,
                                                        border: `1px solid ${insightColor(ins.type)}20`,
                                                    }}>
                                                        <span className="material-symbols-outlined" style={{
                                                            fontSize: 18, color: insightColor(ins.type), flexShrink: 0, marginTop: 1,
                                                        }}>{insightIcon(ins.type)}</span>
                                                        <div style={{ flex: 1 }}>
                                                            <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 4 }}>
                                                                <span style={{
                                                                    fontSize: 9, fontWeight: 700, textTransform: "uppercase",
                                                                    letterSpacing: "0.08em", color: insightColor(ins.type),
                                                                }}>{ins.type.replace("_", " ")}</span>
                                                                <span style={{
                                                                    fontSize: 8, fontWeight: 600, textTransform: "uppercase",
                                                                    color: "rgba(26,26,26,0.35)", letterSpacing: "0.05em",
                                                                    background: "rgba(26,26,26,0.05)", padding: "2px 6px",
                                                                    borderRadius: 4,
                                                                }}>{ins.category}</span>
                                                            </div>
                                                            <LatexText as="p" style={{ margin: 0, fontSize: 13, lineHeight: 1.55, color: "rgba(26,26,26,0.75)", fontWeight: 500 }}>
                                                                {ins.content}
                                                            </LatexText>
                                                        </div>
                                                    </li>
                                                ))}
                                            </ul>
                                        </>
                                    )}

                                    {/* Current concept footer */}
                                    <div style={{ marginTop: 24, paddingTop: 18, borderTop: "1px solid rgba(0,0,0,0.06)" }}>
                                        <p style={{ fontSize: 11, textTransform: "uppercase", fontWeight: 700, color: "rgba(26,26,26,0.4)", marginBottom: 10, letterSpacing: "0.1em" }}>Current Concept</p>
                                        <p style={{
                                            fontSize: 14, color: "rgba(26,26,26,0.8)", lineHeight: 1.5,
                                            background: "rgba(26,26,26,0.03)", padding: "12px 14px",
                                            borderRadius: 10, fontWeight: 700, border: "1px solid rgba(0,0,0,0.05)", margin: 0,
                                        }}>
                                            {selected?.name || "Overview"}
                                        </p>
                                    </div>
                                </div>
                            </div>
                        </div>
                    )}
                </main>

                {/* ── FOOTER NAV ── */}
                <footer style={{
                    position: "fixed", bottom: 40, left: 0, right: 0,
                    display: "flex", justifyContent: "center", alignItems: "center",
                    pointerEvents: "none", zIndex: 60,
                }}>
                    <div style={{ display: "flex", flexWrap: "wrap", justifyContent: "center", alignItems: "center", gap: 24, pointerEvents: "auto", maxWidth: "90vw" }}>

                        {/* Insights / Understanding button (Floating Action) */}
                        <button
                            onClick={() => setShowInsights(true)}
                            style={{
                                display: "flex", alignItems: "center", gap: 8,
                                background: C.dark, color: C.white,
                                border: "none", borderRadius: 999, padding: "12px 24px",
                                cursor: "pointer", fontFamily: "inherit",
                                boxShadow: "0 8px 30px -4px rgba(0,0,0,0.3)",
                                transition: "transform 0.2s cubic-bezier(0.34, 1.56, 0.64, 1), box-shadow 0.2s",
                            }}
                            onMouseEnter={e => { e.currentTarget.style.transform = "scale(1.05) translateY(-2px)"; e.currentTarget.style.boxShadow = "0 12px 40px -8px rgba(0,0,0,0.4)"; }}
                            onMouseLeave={e => { e.currentTarget.style.transform = "scale(1) translateY(0)"; e.currentTarget.style.boxShadow = "0 8px 30px -4px rgba(0,0,0,0.3)"; }}
                        >
                            <span className="material-symbols-outlined" style={{ fontSize: 18 }}>insights</span>
                            <span style={{ fontSize: 11, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.1em" }}>Your Understanding</span>
                        </button>



                    </div>
                </footer>
            </div>
        </>
    );
}

/* ── Small helper for inactive nav pills ── */
function NavPill({ label, icon, onClick }: { label: string; icon: string; onClick?: () => void }) {
    return (
        <button
            onClick={onClick}
            style={{
                padding: "10px 20px", background: "transparent", color: "rgba(26,26,26,0.6)",
                borderRadius: 999, fontSize: 10, fontWeight: 700,
                textTransform: "uppercase", letterSpacing: "0.08em",
                display: "flex", alignItems: "center", gap: 8,
                border: "none", cursor: "pointer", fontFamily: "inherit",
                transition: "all 0.2s",
            }}
            onMouseEnter={e => { e.currentTarget.style.color = "#1a1a1a"; e.currentTarget.style.background = "rgba(26,26,26,0.05)"; }}
            onMouseLeave={e => { e.currentTarget.style.color = "rgba(26,26,26,0.6)"; e.currentTarget.style.background = "transparent"; }}
        >
            <span className="material-symbols-outlined" style={{ fontSize: 14 }}>{icon}</span>
            {label}
        </button>
    );
}
