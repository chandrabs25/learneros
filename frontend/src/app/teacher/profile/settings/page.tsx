"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type Me = {
  uid?: string;
  email?: string;
  name?: string;
  role?: string;
  institute_id?: string;
};

type Institute = {
  id: string;
  name: string;
  location?: string | null;
  description?: string | null;
};

export default function TeacherProfileSettingsPage() {
  const router = useRouter();
  const { user, getIdToken, signOut } = useAuth();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [me, setMe] = useState<Me | null>(null);
  const [institute, setInstitute] = useState<Institute | null>(null);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        setLoading(true);
        const token = await getIdToken();
        if (!token) {
          router.replace("/auth");
          return;
        }

        const meRes = await fetch(`${API_URL}/auth/me`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        const meData: Me = await meRes.json();
        const role = String(meData?.role || "").toLowerCase();
        if (role !== "teacher" && role !== "admin" && role !== "superadmin") {
          router.replace("/profile/settings");
          return;
        }

        if (cancelled) return;
        setMe(meData);

        if (meData?.institute_id) {
          const instRes = await fetch(`${API_URL}/api/institutes`);
          const all = await instRes.json();
          if (!cancelled && Array.isArray(all)) {
            const matched = all.find((i: Institute) => i.id === meData.institute_id) || null;
            setInstitute(matched);
          }
        }
      } catch (e: unknown) {
        if (!cancelled) setError(e instanceof Error ? e.message : "Failed to load profile");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [getIdToken, router]);

  const deleteProfile = async () => {
    const ok = window.confirm("Delete your profile permanently? This cannot be undone.");
    if (!ok) return;
    setDeleting(true);
    setError("");
    try {
      const token = await getIdToken();
      if (!token) throw new Error("Missing token");
      const res = await fetch(`${API_URL}/auth/me`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data?.detail || "Failed to delete profile");
      await signOut();
      router.replace("/auth");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to delete profile");
      setDeleting(false);
    }
  };

  if (loading) {
    return (
      <main style={{ padding: "1.5rem", color: "#64748b", fontWeight: 700 }}>
        Loading teacher profile...
      </main>
    );
  }

  return (
    <main style={{ background: "#f5f8f8", minHeight: "calc(100vh - 72px)", padding: "1.2rem 1.6rem 2rem" }}>
      <div style={{ maxWidth: 920, margin: "0 auto", display: "flex", flexDirection: "column", gap: "1rem" }}>
        <h1 style={{ margin: 0 }}>Teacher Profile Settings</h1>
        <p style={{ margin: 0, color: "#64748b", fontWeight: 600 }}>
          Account details for teacher dashboard access.
        </p>

        {error && (
          <div style={{ background: "#fff1f2", border: "1px solid #fecdd3", color: "#be123c", borderRadius: 10, padding: "0.7rem 0.9rem", fontWeight: 700 }}>
            {error}
          </div>
        )}

        <section style={{ background: "#fff", border: "1px solid #e2e8f0", borderRadius: 12, padding: "1rem" }}>
          <h2 style={{ marginTop: 0 }}>Identity</h2>
          <div style={{ display: "grid", gridTemplateColumns: "170px 1fr", gap: "0.5rem 0.8rem", alignItems: "baseline" }}>
            <div style={{ color: "#64748b", fontWeight: 700 }}>Name</div>
            <div style={{ fontWeight: 800 }}>{user?.displayName || me?.name || "-"}</div>
            <div style={{ color: "#64748b", fontWeight: 700 }}>Email</div>
            <div style={{ fontWeight: 800 }}>{user?.email || me?.email || "-"}</div>
            <div style={{ color: "#64748b", fontWeight: 700 }}>Role</div>
            <div style={{ fontWeight: 800, textTransform: "capitalize" }}>{String(me?.role || "teacher")}</div>
            <div style={{ color: "#64748b", fontWeight: 700 }}>UID</div>
            <div style={{ fontWeight: 800, wordBreak: "break-all" }}>{me?.uid || "-"}</div>
          </div>
        </section>

        <section style={{ background: "#fff", border: "1px solid #e2e8f0", borderRadius: 12, padding: "1rem" }}>
          <h2 style={{ marginTop: 0 }}>Institute Scope</h2>
          <div style={{ display: "grid", gridTemplateColumns: "170px 1fr", gap: "0.5rem 0.8rem", alignItems: "baseline" }}>
            <div style={{ color: "#64748b", fontWeight: 700 }}>Institute ID</div>
            <div style={{ fontWeight: 800 }}>{me?.institute_id || "Not set"}</div>
            <div style={{ color: "#64748b", fontWeight: 700 }}>Institute Name</div>
            <div style={{ fontWeight: 800 }}>{institute?.name || "-"}</div>
            <div style={{ color: "#64748b", fontWeight: 700 }}>Location</div>
            <div style={{ fontWeight: 800 }}>{institute?.location || "-"}</div>
          </div>
          <p style={{ margin: "0.85rem 0 0", color: "#64748b", fontWeight: 600 }}>
            To change role or institute claims, use Admin Dashboard.
          </p>
        </section>

        <section style={{ background: "#fff", border: "1px solid #fecdd3", borderRadius: 12, padding: "1rem" }}>
          <h2 style={{ marginTop: 0, color: "#be123c" }}>Danger Zone</h2>
          <p style={{ color: "#64748b", marginTop: 0 }}>
            Delete your account permanently. This removes teacher profile and linked student graph data.
          </p>
          <button
            onClick={deleteProfile}
            disabled={deleting}
            style={{
              border: "none",
              borderRadius: 8,
              background: "#ef4444",
              color: "#fff",
              padding: "0.6rem 0.95rem",
              fontWeight: 800,
              cursor: deleting ? "not-allowed" : "pointer",
              opacity: deleting ? 0.65 : 1,
            }}
          >
            {deleting ? "Deleting..." : "Delete Profile"}
          </button>
        </section>
      </div>
    </main>
  );
}
