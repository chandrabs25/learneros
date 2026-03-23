"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type Institute = {
  id: string;
  name: string;
  location?: string | null;
  description?: string | null;
  logo?: string | null;
};

type Me = { role?: string; uid?: string; email?: string; name?: string };
type TeacherApplication = {
  id: string;
  status: "PENDING" | "APPROVED" | "REJECTED" | "SUPERSEDED" | string;
  applicant_uid?: string | null;
  applicant_email?: string | null;
  applicant_name?: string | null;
  institute_id?: string | null;
  institute_name?: string | null;
  department?: string | null;
  statement?: string | null;
  note?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
};

export default function AdminDashboardPage() {
  const router = useRouter();
  const { getIdToken } = useAuth();

  const [checking, setChecking] = useState(true);
  const [role, setRole] = useState("");
  const [institutes, setInstitutes] = useState<Institute[]>([]);
  const [msg, setMsg] = useState("");
  const [err, setErr] = useState("");

  const [instName, setInstName] = useState("");
  const [instLocation, setInstLocation] = useState("");
  const [instDescription, setInstDescription] = useState("");

  const [userEmail, setUserEmail] = useState("");
  const [userUid, setUserUid] = useState("");
  const [targetRole, setTargetRole] = useState<"student" | "teacher" | "admin" | "superadmin">("teacher");
  const [targetInstitute, setTargetInstitute] = useState("");
  const [claimLookup, setClaimLookup] = useState("");
  const [claimResult, setClaimResult] = useState("");
  const [applications, setApplications] = useState<TeacherApplication[]>([]);
  const [appFilter, setAppFilter] = useState<"PENDING" | "APPROVED" | "REJECTED" | "SUPERSEDED" | "ALL">("PENDING");
  const [appBusyId, setAppBusyId] = useState("");
  const [reviewNotes, setReviewNotes] = useState<Record<string, string>>({});

  const loadApplications = useCallback(async (token?: string | null, status: "PENDING" | "APPROVED" | "REJECTED" | "SUPERSEDED" | "ALL" = appFilter) => {
    const tk = token || (await getIdToken());
    if (!tk) throw new Error("Missing token");
    const query = status === "ALL" ? "" : `?status=${encodeURIComponent(status)}`;
    const res = await fetch(`${API_URL}/api/admin/teacher-applications${query}`, {
      headers: { Authorization: `Bearer ${tk}` },
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data?.detail || "Failed to load applications");
    setApplications(Array.isArray(data) ? data : []);
  }, [appFilter, getIdToken]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const token = await getIdToken();
        if (!token) {
          router.push("/auth");
          return;
        }
        const [meRes, instRes] = await Promise.all([
          fetch(`${API_URL}/auth/me`, { headers: { Authorization: `Bearer ${token}` } }),
          fetch(`${API_URL}/api/institutes`),
        ]);
        const me: Me = await meRes.json();
        const inst = await instRes.json();
        const r = String(me?.role || "").toLowerCase();
        if (!cancelled) {
          setRole(r);
          setInstitutes(Array.isArray(inst) ? inst : []);
          if ((Array.isArray(inst) ? inst.length : 0) > 0) {
            setTargetInstitute(inst[0].id);
          }
        }
        await loadApplications(token, "PENDING");
      } catch {
        if (!cancelled) setErr("Failed to load admin context.");
      } finally {
        if (!cancelled) setChecking(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [getIdToken, router, loadApplications]);

  const isAdmin = role === "admin" || role === "superadmin";

  const createInstitute = async () => {
    setErr("");
    setMsg("");
    try {
      const token = await getIdToken();
      if (!token) throw new Error("Missing token");
      const res = await fetch(`${API_URL}/api/admin/institutes`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify({
          name: instName,
          location: instLocation || null,
          description: instDescription || null,
          is_active: true,
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data?.detail || "Create institute failed");
      setMsg(`Institute created: ${data.id}`);
      setInstName("");
      setInstLocation("");
      setInstDescription("");
      const listRes = await fetch(`${API_URL}/api/institutes`);
      const list = await listRes.json();
      setInstitutes(Array.isArray(list) ? list : []);
    } catch (e: unknown) {
      setErr(e instanceof Error ? e.message : "Failed");
    }
  };

  const assignClaims = async () => {
    setErr("");
    setMsg("");
    try {
      const token = await getIdToken();
      if (!token) throw new Error("Missing token");
      const body: Record<string, string> = { role: targetRole };
      if (userUid.trim()) body.uid = userUid.trim();
      else if (userEmail.trim()) body.email = userEmail.trim();
      else throw new Error("Provide UID or email");
      if (targetRole === "teacher") {
        if (!targetInstitute) throw new Error("Select institute for teacher role");
        body.institute_id = targetInstitute;
      }
      const res = await fetch(`${API_URL}/api/admin/users/claims`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data?.detail || "Claim update failed");
      setMsg(`Claims updated for uid=${data.uid}. Ask user to refresh token.`);
    } catch (e: unknown) {
      setErr(e instanceof Error ? e.message : "Failed");
    }
  };

  const lookupClaims = async () => {
    setErr("");
    setMsg("");
    setClaimResult("");
    try {
      const token = await getIdToken();
      if (!token) throw new Error("Missing token");
      const query = claimLookup.includes("@")
        ? `email=${encodeURIComponent(claimLookup.trim())}`
        : `uid=${encodeURIComponent(claimLookup.trim())}`;
      const res = await fetch(`${API_URL}/api/admin/users/claims?${query}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data?.detail || "Lookup failed");
      setClaimResult(JSON.stringify(data, null, 2));
    } catch (e: unknown) {
      setErr(e instanceof Error ? e.message : "Failed");
    }
  };

  const reviewApplication = async (applicationId: string, action: "approve" | "reject") => {
    setErr("");
    setMsg("");
    try {
      const token = await getIdToken();
      if (!token) throw new Error("Missing token");
      setAppBusyId(applicationId);
      const res = await fetch(`${API_URL}/api/admin/teacher-applications/${encodeURIComponent(applicationId)}/${action}`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify({ note: (reviewNotes[applicationId] || "").trim() || null }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data?.detail || `Failed to ${action} application`);
      setMsg(`Application ${action === "approve" ? "approved" : "rejected"}: ${applicationId}`);
      await loadApplications(token, appFilter);
    } catch (e: unknown) {
      setErr(e instanceof Error ? e.message : `Failed to ${action}`);
    } finally {
      setAppBusyId("");
    }
  };

  if (checking) {
    return <main style={{ padding: "1.5rem", color: "#64748b", fontWeight: 700 }}>Loading admin dashboard...</main>;
  }

  if (!isAdmin) {
    return (
      <main style={{ padding: "1.5rem" }}>
        <div style={{ background: "#fff1f2", border: "1px solid #fecdd3", color: "#be123c", padding: "0.9rem 1rem", borderRadius: 12, fontWeight: 700 }}>
          Admin role required to access this page.
        </div>
      </main>
    );
  }

  return (
    <main style={{ background: "#f5f8f8", minHeight: "calc(100vh - 72px)", padding: "1.2rem 1.6rem 2rem" }}>
      <div style={{ maxWidth: 1100, margin: "0 auto", display: "flex", flexDirection: "column", gap: "1rem" }}>
        <h1 style={{ margin: 0 }}>Admin Dashboard</h1>
        <p style={{ margin: 0, color: "#64748b", fontWeight: 600 }}>Manage institutes and assign teacher/admin claims without scripts.</p>

        {msg && <div style={{ background: "#ecfeff", border: "1px solid #a5f3fc", color: "#0e7490", borderRadius: 10, padding: "0.7rem 0.9rem", fontWeight: 700 }}>{msg}</div>}
        {err && <div style={{ background: "#fff1f2", border: "1px solid #fecdd3", color: "#be123c", borderRadius: 10, padding: "0.7rem 0.9rem", fontWeight: 700 }}>{err}</div>}

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}>
          <section style={{ background: "#fff", border: "1px solid #e2e8f0", borderRadius: 12, padding: "1rem" }}>
            <h2 style={{ marginTop: 0 }}>Create Institute</h2>
            <div style={{ display: "flex", flexDirection: "column", gap: "0.6rem" }}>
              <input value={instName} onChange={(e) => setInstName(e.target.value)} placeholder="Institute name" style={{ border: "1px solid #cbd5e1", borderRadius: 8, padding: "0.55rem 0.7rem" }} />
              <input value={instLocation} onChange={(e) => setInstLocation(e.target.value)} placeholder="Location (optional)" style={{ border: "1px solid #cbd5e1", borderRadius: 8, padding: "0.55rem 0.7rem" }} />
              <textarea value={instDescription} onChange={(e) => setInstDescription(e.target.value)} placeholder="Description (optional)" rows={3} style={{ border: "1px solid #cbd5e1", borderRadius: 8, padding: "0.55rem 0.7rem", resize: "vertical" }} />
              <button onClick={createInstitute} disabled={!instName.trim()} style={{ border: "none", borderRadius: 8, background: "#22d3ee", color: "#083344", padding: "0.55rem 0.8rem", fontWeight: 800, cursor: !instName.trim() ? "not-allowed" : "pointer", opacity: !instName.trim() ? 0.6 : 1 }}>
                Create Institute
              </button>
            </div>
          </section>

          <section style={{ background: "#fff", border: "1px solid #e2e8f0", borderRadius: 12, padding: "1rem" }}>
            <h2 style={{ marginTop: 0 }}>Assign User Role/Claims</h2>
            <div style={{ display: "flex", flexDirection: "column", gap: "0.6rem" }}>
              <input value={userUid} onChange={(e) => setUserUid(e.target.value)} placeholder="Firebase UID (preferred)" style={{ border: "1px solid #cbd5e1", borderRadius: 8, padding: "0.55rem 0.7rem" }} />
              <input value={userEmail} onChange={(e) => setUserEmail(e.target.value)} placeholder="or user email" style={{ border: "1px solid #cbd5e1", borderRadius: 8, padding: "0.55rem 0.7rem" }} />
              <select value={targetRole} onChange={(e) => setTargetRole(e.target.value as "student" | "teacher" | "admin" | "superadmin")} style={{ border: "1px solid #cbd5e1", borderRadius: 8, padding: "0.55rem 0.7rem" }}>
                <option value="teacher">teacher</option>
                <option value="student">student</option>
                <option value="admin">admin</option>
                <option value="superadmin">superadmin</option>
              </select>
              {targetRole === "teacher" && (
                <select value={targetInstitute} onChange={(e) => setTargetInstitute(e.target.value)} style={{ border: "1px solid #cbd5e1", borderRadius: 8, padding: "0.55rem 0.7rem" }}>
                  <option value="">Select institute</option>
                  {institutes.map((i) => (
                    <option key={i.id} value={i.id}>
                      {i.name} ({i.id})
                    </option>
                  ))}
                </select>
              )}
              <button onClick={assignClaims} style={{ border: "none", borderRadius: 8, background: "#22d3ee", color: "#083344", padding: "0.55rem 0.8rem", fontWeight: 800, cursor: "pointer" }}>
                Apply Claims
              </button>
            </div>
          </section>
        </div>

        <section style={{ background: "#fff", border: "1px solid #e2e8f0", borderRadius: 12, padding: "1rem" }}>
          <h2 style={{ marginTop: 0 }}>Lookup Current Claims</h2>
          <div style={{ display: "flex", gap: "0.6rem", flexWrap: "wrap" }}>
            <input value={claimLookup} onChange={(e) => setClaimLookup(e.target.value)} placeholder="UID or email" style={{ flex: 1, minWidth: 260, border: "1px solid #cbd5e1", borderRadius: 8, padding: "0.55rem 0.7rem" }} />
            <button onClick={lookupClaims} disabled={!claimLookup.trim()} style={{ border: "none", borderRadius: 8, background: "#0f172a", color: "#fff", padding: "0.55rem 0.8rem", fontWeight: 800, cursor: !claimLookup.trim() ? "not-allowed" : "pointer", opacity: !claimLookup.trim() ? 0.6 : 1 }}>
              Lookup
            </button>
          </div>
          <pre style={{ marginTop: "0.8rem", background: "#0f172a", color: "#e2e8f0", borderRadius: 10, padding: "0.8rem", overflowX: "auto", minHeight: 120 }}>
            {claimResult || "No lookup yet."}
          </pre>
        </section>

        <section style={{ background: "#fff", border: "1px solid #e2e8f0", borderRadius: 12, padding: "1rem" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12, flexWrap: "wrap", marginBottom: "0.8rem" }}>
            <h2 style={{ margin: 0 }}>Teacher Applications Review</h2>
            <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
              <select
                value={appFilter}
                onChange={async (e) => {
                  const next = e.target.value as "PENDING" | "APPROVED" | "REJECTED" | "SUPERSEDED" | "ALL";
                  setAppFilter(next);
                  try {
                    setErr("");
                    await loadApplications(undefined, next);
                  } catch (error: unknown) {
                    setErr(error instanceof Error ? error.message : "Failed to load applications");
                  }
                }}
                style={{ border: "1px solid #cbd5e1", borderRadius: 8, padding: "0.5rem 0.65rem" }}
              >
                <option value="PENDING">Pending</option>
                <option value="APPROVED">Approved</option>
                <option value="REJECTED">Rejected</option>
                <option value="SUPERSEDED">Superseded</option>
                <option value="ALL">All</option>
              </select>
              <button
                onClick={async () => {
                  try {
                    setErr("");
                    await loadApplications();
                  } catch (error: unknown) {
                    setErr(error instanceof Error ? error.message : "Failed to refresh");
                  }
                }}
                style={{ border: "1px solid #cbd5e1", background: "#fff", borderRadius: 8, padding: "0.5rem 0.7rem", fontWeight: 800, cursor: "pointer" }}
              >
                Refresh
              </button>
            </div>
          </div>

          {applications.length === 0 ? (
            <div style={{ border: "1px dashed #cbd5e1", borderRadius: 10, padding: "0.9rem", color: "#64748b", fontWeight: 700 }}>
              No applications found for selected filter.
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: "0.7rem" }}>
              {applications.map((app) => {
                const isPending = String(app.status).toUpperCase() === "PENDING";
                const busy = appBusyId === app.id;
                return (
                  <article key={app.id} style={{ border: "1px solid #e2e8f0", borderRadius: 10, padding: "0.8rem" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", gap: 8, flexWrap: "wrap" }}>
                      <div>
                        <div style={{ fontWeight: 900 }}>{app.applicant_name || app.applicant_email || app.applicant_uid || "Unknown applicant"}</div>
                        <div style={{ color: "#64748b", fontSize: 13, fontWeight: 600 }}>
                          {app.applicant_email || app.applicant_uid || "No user identity"} • {app.institute_name || app.institute_id || "No institute"}
                        </div>
                      </div>
                      <span
                        style={{
                          background: isPending ? "#fff7ed" : "#f1f5f9",
                          color: isPending ? "#9a3412" : "#334155",
                          borderRadius: 999,
                          fontWeight: 900,
                          fontSize: 12,
                          padding: "0.2rem 0.6rem",
                          height: "fit-content",
                        }}
                      >
                        {app.status}
                      </span>
                    </div>

                    {app.department && <div style={{ marginTop: 6, color: "#0f172a", fontWeight: 700 }}>Department: {app.department}</div>}
                    {app.statement && (
                      <div style={{ marginTop: 6, color: "#334155", fontWeight: 600, whiteSpace: "pre-wrap" }}>{app.statement}</div>
                    )}
                    {app.note && <div style={{ marginTop: 6, color: "#be123c", fontWeight: 700 }}>Review note: {app.note}</div>}

                    {isPending && (
                      <div style={{ marginTop: "0.7rem", display: "flex", flexDirection: "column", gap: "0.55rem" }}>
                        <input
                          value={reviewNotes[app.id] || ""}
                          onChange={(e) => setReviewNotes((prev) => ({ ...prev, [app.id]: e.target.value }))}
                          placeholder="Optional admin note"
                          style={{ border: "1px solid #cbd5e1", borderRadius: 8, padding: "0.5rem 0.65rem" }}
                        />
                        <div style={{ display: "flex", gap: "0.5rem", justifyContent: "flex-end" }}>
                          <button
                            onClick={() => reviewApplication(app.id, "reject")}
                            disabled={busy}
                            style={{
                              border: "1px solid #fecdd3",
                              borderRadius: 8,
                              background: busy ? "#ffe4e6" : "#fff1f2",
                              color: "#be123c",
                              padding: "0.5rem 0.7rem",
                              fontWeight: 800,
                              cursor: busy ? "not-allowed" : "pointer",
                            }}
                          >
                            Reject
                          </button>
                          <button
                            onClick={() => reviewApplication(app.id, "approve")}
                            disabled={busy}
                            style={{
                              border: "none",
                              borderRadius: 8,
                              background: busy ? "#a5f3fc" : "#22d3ee",
                              color: "#083344",
                              padding: "0.5rem 0.7rem",
                              fontWeight: 800,
                              cursor: busy ? "not-allowed" : "pointer",
                            }}
                          >
                            Approve
                          </button>
                        </div>
                      </div>
                    )}
                  </article>
                );
              })}
            </div>
          )}
        </section>

        {/* Rebuild Student Clusters */}
        <section style={{ background: "#fff", border: "1px solid #e2e8f0", borderRadius: 12, padding: "1rem" }}>
          <h2 style={{ marginTop: 0, display: "flex", alignItems: "center", gap: "0.4rem" }}>
            <span style={{ fontSize: "1.1rem" }}>🔄</span> Rebuild Student Clusters
          </h2>
          <p style={{ color: "#64748b", fontWeight: 600, fontSize: "0.88rem", margin: "0 0 0.7rem" }}>
            Trigger HDBSCAN/K-Means clustering for all institutes. Creates a new snapshot for the teacher dashboard.
          </p>
          <div style={{ display: "flex", gap: "0.6rem", alignItems: "center", flexWrap: "wrap" }}>
            <button
              id="rebuild-clusters-btn"
              onClick={async () => {
                setErr("");
                setMsg("");
                try {
                  const token = await getIdToken();
                  if (!token) throw new Error("Missing token");
                  const res = await fetch(`${API_URL}/api/admin/rebuild-clusters`, {
                    method: "POST",
                    headers: { Authorization: `Bearer ${token}` },
                  });
                  const data = await res.json();
                  if (!res.ok) throw new Error(data?.detail || "Failed to start rebuild");
                  setMsg(data.message || "Rebuild started");
                  // Poll for status
                  const poll = setInterval(async () => {
                    try {
                      const sRes = await fetch(`${API_URL}/api/admin/rebuild-clusters/status`, {
                        headers: { Authorization: `Bearer ${token}` },
                      });
                      const sData = await sRes.json();
                      if (sData.state === "done") {
                        clearInterval(poll);
                        const results = sData.results || [];
                        const summary = results.map((r: Record<string, unknown>) => `${r.institute_id}: ${r.status}`).join(", ");
                        setMsg(`Clusters rebuilt! ${summary}`);
                      } else if (sData.state === "error") {
                        clearInterval(poll);
                        setErr(`Rebuild failed: ${sData.error || "unknown"}`);
                      }
                    } catch {
                      clearInterval(poll);
                    }
                  }, 3000);
                } catch (e: unknown) {
                  setErr(e instanceof Error ? e.message : "Failed");
                }
              }}
              style={{ border: "none", borderRadius: 8, background: "linear-gradient(135deg, #6366f1, #8b5cf6)", color: "#fff", padding: "0.6rem 1rem", fontWeight: 800, cursor: "pointer", fontSize: "0.88rem" }}
            >
              🔄 Rebuild All Clusters
            </button>
          </div>
        </section>
      </div>
    </main>
  );
}
