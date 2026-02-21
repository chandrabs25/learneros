"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Institute {
    id: string;
    name: string;
    location: string;
    description: string;
    logo: string | null;
}

export default function InstitutePage() {
    const { user, loading, getIdToken } = useAuth();
    const router = useRouter();
    const [institutes, setInstitutes] = useState<Institute[]>([]);
    const [selected, setSelected] = useState<string | null>(null);
    const [saving, setSaving] = useState(false);
    const [fetchingCurrent, setFetchingCurrent] = useState(true);
    const [loadError, setLoadError] = useState("");

    // Redirect unauthenticated users to home
    useEffect(() => {
        if (!loading && !user) {
            router.replace("/");
        }
    }, [loading, user, router]);

    // Load available institutes
    useEffect(() => {
        const controller = new AbortController();
        (async () => {
            try {
                setLoadError("");
                const r = await fetch(`${API_URL}/api/institutes`, { signal: controller.signal });
                if (!r.ok) throw new Error(`Failed to load institutes (${r.status})`);
                const data = await r.json();
                setInstitutes(Array.isArray(data) ? data : []);
            } catch (err: unknown) {
                if (controller.signal.aborted) return;
                setInstitutes([]);
                setLoadError(
                    err instanceof Error && err.message
                        ? err.message
                        : "Could not reach backend. Check if API server is running on port 8000."
                );
            }
        })();
        return () => controller.abort();
    }, []);

    // Pre-select if student already has an institute
    useEffect(() => {
        if (!user) return;
        const fetchCurrent = async () => {
            const token = await getIdToken();
            if (!token) return;
            try {
                const res = await fetch(`${API_URL}/api/students/me/institute`, {
                    headers: { Authorization: `Bearer ${token}` },
                });
                const data = await res.json();
                if (data.institute?.id) {
                    // Already has institute — skip to hub
                    router.replace("/");
                }
            } catch {
                // Ignore — let them pick
            } finally {
                setFetchingCurrent(false);
            }
        };
        fetchCurrent();
    }, [user, getIdToken, router]);

    const handleConfirm = async () => {
        if (!selected) return;
        setSaving(true);
        try {
            const token = await getIdToken();
            if (!token) throw new Error("You are signed out. Please sign in again.");
            const res = await fetch(`${API_URL}/api/students/me/institute`, {
                method: "PATCH",
                headers: {
                    "Content-Type": "application/json",
                    Authorization: `Bearer ${token}`,
                },
                body: JSON.stringify({ institute_id: selected }),
            });
            if (!res.ok) {
                const data = await res.json().catch(() => ({}));
                throw new Error(data?.detail || `Failed to save institute (${res.status})`);
            }
            router.replace("/");
        } catch (e: unknown) {
            setLoadError(e instanceof Error ? e.message : "Failed to save institute");
            setSaving(false);
        }
    };

    if (loading || fetchingCurrent) {
        return (
            <div className="onboarding-page">
                <div className="spinner" />
            </div>
        );
    }

    return (
        <div className="onboarding-page">
            <div className="onboarding-card">
                {/* Header */}
                <div className="onboarding-header">
                    <div className="onboarding-step">Step 1 of 1</div>
                    <h1>Which institute are you from?</h1>
                    <p>We&apos;ll personalise your experience based on your institute&apos;s curriculum and schedule.</p>
                </div>

                {/* Institute List */}
                <div className="institute-list">
                    {!!loadError && (
                        <div style={{ color: "#b91c1c", padding: "0.5rem 0.25rem" }}>{loadError}</div>
                    )}
                    {institutes.map((inst) => (
                        <button
                            key={inst.id}
                            className={`institute-card ${selected === inst.id ? "institute-selected" : ""}`}
                            onClick={() => setSelected(inst.id)}
                        >
                            <div className="institute-logo-placeholder">
                                {inst.logo ? (
                                    <img src={inst.logo} alt={inst.name} />
                                ) : (
                                    <span className="material-symbols-outlined">school</span>
                                )}
                            </div>
                            <div className="institute-info">
                                <span className="institute-name">{inst.name}</span>
                                <span className="institute-location">{inst.location}</span>
                                <span className="institute-desc">{inst.description}</span>
                            </div>
                            {selected === inst.id && (
                                <span className="material-symbols-outlined institute-check">check_circle</span>
                            )}
                        </button>
                    ))}
                </div>

                {/* Skip + Confirm */}
                <div className="onboarding-actions">
                    <button
                        className="onboarding-skip"
                        onClick={() => router.replace("/")}
                    >
                        Skip for now
                    </button>
                    <button
                        className={`onboarding-confirm ${!selected ? "onboarding-confirm-disabled" : ""}`}
                        onClick={handleConfirm}
                        disabled={!selected || saving}
                    >
                        {saving ? "Saving..." : "Confirm"}
                        {!saving && <span className="material-symbols-outlined">arrow_forward</span>}
                    </button>
                </div>
            </div>
        </div>
    );
}
