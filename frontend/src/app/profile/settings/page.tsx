"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Institute {
  id: string;
  name: string;
  location?: string | null;
  description?: string | null;
  logo?: string | null;
}

interface StudentProfile {
  student_id: string;
  name?: string;
  email?: string;
  grade?: number | null;
  institute?: Institute | { id: string } | null;
}

type Me = { role?: string };

const GRADES = Array.from({ length: 7 }, (_, i) => i + 6); // 6..12

export default function ProfileSettingsPage() {
  const router = useRouter();
  const { getIdToken, signOut } = useAuth();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [profile, setProfile] = useState<StudentProfile | null>(null);
  const [institutes, setInstitutes] = useState<Institute[]>([]);
  const [selectedInstitute, setSelectedInstitute] = useState("");
  const [selectedGrade, setSelectedGrade] = useState<string>("");
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError("");
      try {
        const token = await getIdToken();
        if (!token) {
          router.push("/auth");
          return;
        }
        const [meRes, pRes, iRes] = await Promise.all([
          fetch(`${API_URL}/auth/me`, {
            headers: { Authorization: `Bearer ${token}` },
          }),
          fetch(`${API_URL}/api/students/me/profile`, {
            headers: { Authorization: `Bearer ${token}` },
          }),
          fetch(`${API_URL}/api/institutes`),
        ]);
        const [meData, pData, iData] = await Promise.all([meRes.json(), pRes.json(), iRes.json()]);
        const role = String((meData as Me)?.role || "").toLowerCase();
        if (role === "teacher" || role === "admin" || role === "superadmin") {
          router.replace("/teacher/profile/settings");
          return;
        }
        if (!pRes.ok) throw new Error(pData?.detail || "Failed to load profile");
        if (!cancelled) {
          setProfile(pData);
          setInstitutes(Array.isArray(iData) ? iData : []);
          const instId = pData?.institute?.id || "";
          setSelectedInstitute(instId);
          setSelectedGrade(
            pData?.grade === null || pData?.grade === undefined ? "" : String(pData.grade)
          );
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

  const saveInstitute = async () => {
    setSaving(true);
    setError("");
    setSuccess("");
    try {
      const token = await getIdToken();
      if (!token) throw new Error("Missing token");
      const payload = { institute_id: selectedInstitute || null };
      const res = await fetch(`${API_URL}/api/students/me/profile`, {
        method: "PATCH",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data?.detail || "Failed to update institute");
      setProfile(data);
      setSelectedInstitute(data?.institute?.id || "");
      setSuccess("Institute updated.");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to update institute");
    } finally {
      setSaving(false);
    }
  };

  const saveGrade = async () => {
    setSaving(true);
    setError("");
    setSuccess("");
    try {
      const token = await getIdToken();
      if (!token) throw new Error("Missing token");
      const payload = { grade: selectedGrade ? Number(selectedGrade) : null };
      const res = await fetch(`${API_URL}/api/students/me/profile`, {
        method: "PATCH",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data?.detail || "Failed to update grade");
      setProfile(data);
      setSelectedGrade(
        data?.grade === null || data?.grade === undefined ? "" : String(data.grade)
      );
      setSuccess("Grade updated.");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to update grade");
    } finally {
      setSaving(false);
    }
  };

  const deleteProfile = async () => {
    const ok = window.confirm("Delete your profile permanently? This cannot be undone.");
    if (!ok) return;
    setDeleting(true);
    setError("");
    setSuccess("");
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
        Loading profile settings...
      </main>
    );
  }

  return (
    <main style={{ background: "#f5f8f8", minHeight: "calc(100vh - 72px)", padding: "1.2rem 1.6rem 2rem" }}>
      <div style={{ maxWidth: 920, margin: "0 auto", display: "flex", flexDirection: "column", gap: "1rem" }}>
        <h1 style={{ margin: 0 }}>Profile Settings</h1>
        <p style={{ margin: 0, color: "#64748b", fontWeight: 600 }}>
          Manage your institute and grade preferences.
        </p>

        {error && (
          <div style={{ background: "#fff1f2", border: "1px solid #fecdd3", color: "#be123c", borderRadius: 10, padding: "0.7rem 0.9rem", fontWeight: 700 }}>
            {error}
          </div>
        )}
        {success && (
          <div style={{ background: "#ecfeff", border: "1px solid #a5f3fc", color: "#0e7490", borderRadius: 10, padding: "0.7rem 0.9rem", fontWeight: 700 }}>
            {success}
          </div>
        )}

        <section style={{ background: "#fff", border: "1px solid #e2e8f0", borderRadius: 12, padding: "1rem" }}>
          <h2 style={{ marginTop: 0 }}>Institute</h2>
          <p style={{ color: "#64748b", marginTop: 0 }}>
            Current: <strong>{profile?.institute?.id || "Not set"}</strong>
          </p>
          <div style={{ display: "flex", gap: "0.6rem", flexWrap: "wrap" }}>
            <select
              value={selectedInstitute}
              onChange={(e) => setSelectedInstitute(e.target.value)}
              style={{ flex: 1, minWidth: 320, border: "1px solid #cbd5e1", borderRadius: 8, padding: "0.55rem 0.7rem", background: "#fff" }}
            >
              <option value="">Remove institute</option>
              {institutes.map((inst) => (
                <option key={inst.id} value={inst.id}>
                  {inst.name} ({inst.id})
                </option>
              ))}
            </select>
            <button
              onClick={saveInstitute}
              disabled={saving}
              style={{ border: "none", borderRadius: 8, background: "#22d3ee", color: "#083344", padding: "0.55rem 0.8rem", fontWeight: 800, cursor: saving ? "not-allowed" : "pointer", opacity: saving ? 0.6 : 1 }}
            >
              Save Institute
            </button>
          </div>
        </section>

        <section style={{ background: "#fff", border: "1px solid #e2e8f0", borderRadius: 12, padding: "1rem" }}>
          <h2 style={{ marginTop: 0 }}>Grade</h2>
          <p style={{ color: "#64748b", marginTop: 0 }}>
            Current: <strong>{profile?.grade ?? "Not set"}</strong>
          </p>
          <div style={{ display: "flex", gap: "0.6rem", flexWrap: "wrap" }}>
            <select
              value={selectedGrade}
              onChange={(e) => setSelectedGrade(e.target.value)}
              style={{ flex: 1, minWidth: 320, border: "1px solid #cbd5e1", borderRadius: 8, padding: "0.55rem 0.7rem", background: "#fff" }}
            >
              <option value="">Remove grade</option>
              {GRADES.map((g) => (
                <option key={g} value={String(g)}>
                  Class {g}
                </option>
              ))}
            </select>
            <button
              onClick={saveGrade}
              disabled={saving}
              style={{ border: "none", borderRadius: 8, background: "#22d3ee", color: "#083344", padding: "0.55rem 0.8rem", fontWeight: 800, cursor: saving ? "not-allowed" : "pointer", opacity: saving ? 0.6 : 1 }}
            >
              Save Grade
            </button>
          </div>
        </section>

        <section style={{ background: "#fff", border: "1px solid #fecdd3", borderRadius: 12, padding: "1rem" }}>
          <h2 style={{ marginTop: 0, color: "#be123c" }}>Danger Zone</h2>
          <p style={{ color: "#64748b", marginTop: 0 }}>
            Delete your account permanently. This removes your profile and learning history.
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
