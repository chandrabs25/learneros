"use client";

import { CSSProperties, FormEvent, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type Institute = {
  id: string;
  name: string;
  location?: string | null;
  description?: string | null;
};

type ApplicationState = {
  id: string;
  status: "PENDING" | "APPROVED" | "REJECTED" | "SUPERSEDED" | string;
  institute_name?: string | null;
  institute_id?: string | null;
  department?: string | null;
  statement?: string | null;
  note?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
  verification_document_urls?: string[];
};

export default function TeacherApplyPage() {
  const { user, loading, getIdToken } = useAuth();
  const router = useRouter();

  const [institutes, setInstitutes] = useState<Institute[]>([]);
  const [search, setSearch] = useState("");
  const [selectedInstitute, setSelectedInstitute] = useState("");
  const [department, setDepartment] = useState("");
  const [statement, setStatement] = useState("");
  const [docUrlsText, setDocUrlsText] = useState("");

  const [application, setApplication] = useState<ApplicationState | null>(null);
  const [loadingData, setLoadingData] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  useEffect(() => {
    if (!loading && !user) {
      router.replace("/auth");
    }
  }, [loading, user, router]);

  useEffect(() => {
    if (!user) return;

    let cancelled = false;
    (async () => {
      try {
        setLoadingData(true);
        setError(null);
        const token = await getIdToken();
        const headers = token ? { Authorization: `Bearer ${token}` } : undefined;

        const [instRes, appRes] = await Promise.all([
          fetch(`${API_URL}/api/institutes`),
          fetch(`${API_URL}/api/teachers/apply/me`, { headers }),
        ]);

        const instData = await instRes.json();
        const appData = await appRes.json();

        if (!cancelled) {
          setInstitutes(Array.isArray(instData) ? instData : []);
          const a = appData?.application ?? null;
          setApplication(a);
          if (a?.institute_id) setSelectedInstitute(String(a.institute_id));
          if (a?.department) setDepartment(String(a.department));
          if (a?.statement) setStatement(String(a.statement));
          if (Array.isArray(a?.verification_document_urls) && a.verification_document_urls.length) {
            setDocUrlsText(a.verification_document_urls.join("\n"));
          }
        }
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : "Failed to load page");
      } finally {
        if (!cancelled) setLoadingData(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [user, getIdToken]);

  const filteredInstitutes = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return institutes;
    return institutes.filter((i) => `${i.name} ${i.location || ""}`.toLowerCase().includes(q));
  }, [institutes, search]);

  const statusColor = (application?.status || "").toUpperCase();
  const statusChipStyle: Record<string, CSSProperties> = {
    APPROVED: { background: "#dcfce7", color: "#166534" },
    PENDING: { background: "#fff7ed", color: "#9a3412" },
    REJECTED: { background: "#fee2e2", color: "#991b1b" },
    SUPERSEDED: { background: "#e2e8f0", color: "#334155" },
  };

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!selectedInstitute) {
      setError("Select an institute first.");
      return;
    }

    try {
      setSubmitting(true);
      setError(null);
      setSuccess(null);
      const token = await getIdToken();
      if (!token) throw new Error("Not authenticated");

      const verification_document_urls = docUrlsText
        .split("\n")
        .map((v) => v.trim())
        .filter(Boolean);

      const res = await fetch(`${API_URL}/api/teachers/apply`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          institute_id: selectedInstitute,
          department: department || null,
          statement: statement || null,
          verification_document_urls,
        }),
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data?.detail || "Application submit failed");

      const current: ApplicationState = {
        id: data?.application?.id,
        status: data?.application?.state || "PENDING",
        institute_id: data?.application?.institute_id,
        institute_name: data?.application?.institute_name,
        department,
        statement,
        verification_document_urls,
      };
      setApplication(current);
      setSuccess("Application submitted. Admin review is pending.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Application submit failed");
    } finally {
      setSubmitting(false);
    }
  };

  if (loading || loadingData) {
    return <div style={{ padding: "2rem", fontWeight: 600 }}>Loading teacher access portal...</div>;
  }

  return (
    <main style={{ maxWidth: 1220, margin: "0 auto", padding: "2rem 1.5rem 3rem" }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "1.25rem" }}>
        <div>
          <h1 style={{ margin: 0, fontSize: "2rem", fontWeight: 900 }}>Teacher Access Request</h1>
          <p style={{ margin: "0.45rem 0 0", color: "#64748b", fontWeight: 600 }}>Apply for teacher access with your institute details.</p>
        </div>
        <button
          onClick={() => router.push("/")}
          style={{ border: "1px solid #cbd5e1", background: "#fff", borderRadius: 10, padding: "0.6rem 0.9rem", fontWeight: 700, cursor: "pointer" }}
        >
          Back to Home
        </button>
      </div>

      {(error || success) && (
        <div
          style={{
            marginBottom: "1rem",
            borderRadius: 12,
            padding: "0.8rem 1rem",
            border: `1px solid ${error ? "#fecaca" : "#bbf7d0"}`,
            background: error ? "#fff1f2" : "#f0fdf4",
            color: error ? "#b91c1c" : "#166534",
            fontWeight: 700,
          }}
        >
          {error || success}
        </div>
      )}

      {application && (
        <section style={{ marginBottom: "1rem", border: "1px solid #e2e8f0", borderRadius: 16, padding: "1rem", background: "#fff" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
            <div>
              <div style={{ color: "#64748b", fontSize: 12, fontWeight: 800, textTransform: "uppercase", letterSpacing: 0.8 }}>Current Request</div>
              <div style={{ fontSize: "1.1rem", fontWeight: 800 }}>{application.institute_name || application.institute_id || "Institute"}</div>
            </div>
            <span
              style={{
                ...statusChipStyle[statusColor],
                padding: "0.25rem 0.6rem",
                borderRadius: 999,
                fontSize: 12,
                fontWeight: 900,
                letterSpacing: 0.6,
              }}
            >
              {statusColor || "UNKNOWN"}
            </span>
          </div>
          {application.note && <div style={{ marginTop: 8, color: "#334155", fontWeight: 600 }}>Admin Note: {application.note}</div>}
        </section>
      )}

      <div className="teacher-apply-grid" style={{ display: "grid", gridTemplateColumns: "minmax(0, 2fr) minmax(0, 1fr)", gap: "1rem" }}>
        <form onSubmit={onSubmit} style={{ background: "#fff", borderRadius: 16, border: "1px solid #e2e8f0", padding: "1.25rem" }}>
          <label style={{ display: "block", fontSize: 13, fontWeight: 800, marginBottom: 6 }}>Find your institute</label>
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search institute by name or location"
            style={{ width: "100%", border: "1px solid #cbd5e1", borderRadius: 10, padding: "0.65rem 0.75rem", marginBottom: "0.55rem" }}
          />
          <div style={{ border: "1px solid #e2e8f0", borderRadius: 10, maxHeight: 210, overflowY: "auto", marginBottom: "0.9rem" }}>
            {filteredInstitutes.length === 0 && <div style={{ padding: "0.8rem", color: "#64748b", fontWeight: 600 }}>No institutes found.</div>}
            {filteredInstitutes.map((inst) => (
              <button
                key={inst.id}
                type="button"
                onClick={() => setSelectedInstitute(inst.id)}
                style={{
                  width: "100%",
                  textAlign: "left",
                  border: "none",
                  borderBottom: "1px solid #f1f5f9",
                  background: selectedInstitute === inst.id ? "#ecfeff" : "#fff",
                  padding: "0.7rem 0.8rem",
                  cursor: "pointer",
                }}
              >
                <div style={{ fontWeight: 800, color: "#0f172a" }}>{inst.name}</div>
                <div style={{ fontSize: 12, color: "#64748b", marginTop: 2 }}>{inst.location || "Location not specified"}</div>
              </button>
            ))}
          </div>

          <label style={{ display: "block", fontSize: 13, fontWeight: 800, marginBottom: 6 }}>Department</label>
          <input
            value={department}
            onChange={(e) => setDepartment(e.target.value)}
            placeholder="e.g. Physics, Mathematics"
            style={{ width: "100%", border: "1px solid #cbd5e1", borderRadius: 10, padding: "0.65rem 0.75rem", marginBottom: "0.9rem" }}
          />

          <label style={{ display: "block", fontSize: 13, fontWeight: 800, marginBottom: 6 }}>Verification document URLs (one per line)</label>
          <textarea
            value={docUrlsText}
            onChange={(e) => setDocUrlsText(e.target.value)}
            placeholder="https://..."
            rows={3}
            style={{ width: "100%", border: "1px solid #cbd5e1", borderRadius: 10, padding: "0.65rem 0.75rem", marginBottom: "0.9rem", resize: "vertical" }}
          />

          <label style={{ display: "block", fontSize: 13, fontWeight: 800, marginBottom: 6 }}>Statement of purpose</label>
          <textarea
            value={statement}
            onChange={(e) => setStatement(e.target.value)}
            placeholder="How will you use the AI tools and analytics for your classroom?"
            rows={6}
            style={{ width: "100%", border: "1px solid #cbd5e1", borderRadius: 10, padding: "0.65rem 0.75rem", resize: "vertical" }}
          />

          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: "1rem", gap: 10, flexWrap: "wrap" }}>
            <span style={{ color: "#64748b", fontSize: 12, fontWeight: 700 }}>Review usually completes in 24-48 hours.</span>
            <button
              type="submit"
              disabled={submitting || !selectedInstitute}
              style={{
                border: "none",
                borderRadius: 10,
                padding: "0.7rem 1.05rem",
                background: submitting || !selectedInstitute ? "#bae6fd" : "#06b6d4",
                color: "#082f49",
                fontWeight: 900,
                cursor: submitting || !selectedInstitute ? "not-allowed" : "pointer",
              }}
            >
              {submitting ? "Submitting..." : "Submit Application"}
            </button>
          </div>
        </form>

        <aside style={{ background: "#ecfeff", borderRadius: 16, border: "1px solid #a5f3fc", padding: "1.15rem" }}>
          <h3 style={{ margin: "0 0 0.5rem", fontSize: "1.1rem", fontWeight: 900 }}>Why verify?</h3>
          <p style={{ margin: 0, color: "#155e75", fontWeight: 600, lineHeight: 1.5 }}>
            Verified teacher accounts can access institute analytics, student risk dashboards, and cluster-level learning insights.
          </p>
          <ul style={{ margin: "0.85rem 0 0", paddingLeft: "1rem", color: "#0f172a", fontWeight: 700, lineHeight: 1.7 }}>
            <li>Institute-scoped teacher dashboard</li>
            <li>Student-level insight drill-down</li>
            <li>Risk bands and cluster summaries</li>
          </ul>
        </aside>
      </div>

      <style jsx>{`
        @media (max-width: 1024px) {
          .teacher-apply-grid {
            grid-template-columns: 1fr !important;
          }
        }
      `}</style>
    </main>
  );
}
