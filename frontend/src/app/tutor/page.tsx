"use client";

import { useEffect, useMemo, useState } from "react";
import { useAuth } from "@/lib/auth-context";
import TutorMarkdown from "@/components/TutorMarkdown";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface InsightItem {
  id: string;
  type: string;
  category: string;
  content: string;
  concept_id?: string;
  concept_name?: string;
  source_id?: string;
  source_title?: string;
  similarity?: number;
}

interface ChatMessage {
  role: "user" | "assistant";
  text: string;
}

interface TutorHistoryMessage {
  role: "user" | "assistant";
  content: string;
}

export default function TutorPage() {
  const { getIdToken } = useAuth();
  const [sessionId, setSessionId] = useState("");
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role: "assistant",
      text: "How can I assist your learning today? I can explain any topic and personalize based on your active insights when relevant.",
    },
  ]);

  const [matchedInsights, setMatchedInsights] = useState<InsightItem[]>([]);
  const [historyLoaded, setHistoryLoaded] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const token = await getIdToken();
        if (!token) {
          if (!cancelled) setHistoryLoaded(true);
          return;
        }
        const res = await fetch(`${API_URL}/api/tutor/session/latest`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data?.detail || `HTTP ${res.status}`);
        const history: TutorHistoryMessage[] = Array.isArray(data?.messages) ? data.messages : [];
        if (!cancelled && data?.session_id && history.length > 0) {
          setSessionId(data.session_id);
          setMessages(history.map((m) => ({ role: m.role, text: m.content })));
        }
      } catch {
        // Keep starter message when history can't be loaded.
      } finally {
        if (!cancelled) setHistoryLoaded(true);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [getIdToken]);

  const matchedConcepts = useMemo(() => {
    const map = new Map<string, { concept: string; count: number; topType?: string }>();
    for (const ins of matchedInsights) {
      const key = ins.concept_id || ins.concept_name || "general";
      const concept = ins.concept_name || (ins.concept_id ? ins.concept_id.replace("concept:", "").replace(/_/g, " ") : "General");
      if (!map.has(key)) map.set(key, { concept, count: 0, topType: ins.type });
      const row = map.get(key)!;
      row.count += 1;
      row.topType = row.topType || ins.type;
    }
    return Array.from(map.values()).sort((a, b) => b.count - a.count);
  }, [matchedInsights]);

  const sendMessage = async (raw: string) => {
    const message = raw.trim();
    if (!message || sending) return;
    setInput("");
    setMessages((prev) => [...prev, { role: "user", text: message }]);
    setSending(true);
    try {
      const token = await getIdToken();
      const headers: Record<string, string> = { "Content-Type": "application/json" };
      if (token) headers.Authorization = `Bearer ${token}`;
      const res = await fetch(`${API_URL}/api/tutor/chat`, {
        method: "POST",
        headers,
        body: JSON.stringify({ message, session_id: sessionId || undefined }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data?.detail || `HTTP ${res.status}`);
      if (!sessionId && data?.session_id) setSessionId(data.session_id);
      const matched = Array.isArray(data?.matched_insights) ? data.matched_insights : [];
      setMatchedInsights(matched);
      setMessages((prev) => [...prev, { role: "assistant", text: data?.response || "I could not generate a response." }]);
    } catch (e: unknown) {
      setMessages((prev) => [...prev, { role: "assistant", text: e instanceof Error ? e.message : "Failed to contact LearnerOS Tutor." }]);
    } finally {
      setSending(false);
    }
  };

  const newExploration = () => {
    setSessionId("");
    setMatchedInsights([]);
    setMessages([
      {
        role: "assistant",
        text: "New exploration started. What topic do you want to learn now?",
      },
    ]);
  };

  return (
    <div className="tutor-layout" style={{ height: "calc(100vh - 64px)", background: "#f8f6f5", overflow: "hidden" }}>
      <aside className="tutor-left" style={{ borderRight: "1px solid #e2e8f0", background: "#fff", padding: "1rem", display: "flex", flexDirection: "column", gap: "1rem", minHeight: 0 }}>
        <div style={{ fontSize: "0.68rem", letterSpacing: "0.12em", fontWeight: 800, textTransform: "uppercase", color: "#94a3b8" }}>Matched Insights</div>
        <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem", overflowY: "auto", minHeight: 0 }}>
          {matchedInsights.length === 0 ? (
            <div style={{ fontSize: "0.85rem", color: "#64748b" }}>No query-matched insights yet. Ask a question to retrieve relevant active insights.</div>
          ) : (
            matchedInsights.map((ins) => (
              <div
                key={ins.id}
                style={{
                  border: "1px solid #fb923c",
                  background: "#fff7ed",
                  borderRadius: 10,
                  padding: "0.6rem",
                }}
              >
                <div style={{ display: "flex", gap: "0.35rem", alignItems: "center", marginBottom: "0.25rem" }}>
                  <span style={{ fontSize: "0.62rem", fontWeight: 800, textTransform: "uppercase", color: "#c2410c" }}>{ins.type.replace(/_/g, " ")}</span>
                  <span style={{ fontSize: "0.62rem", color: "#94a3b8" }}>{ins.category}</span>
                </div>
                <div style={{ fontSize: "0.8rem", fontWeight: 700, color: "#0f172a", marginBottom: "0.2rem" }}>{ins.concept_name || ins.concept_id || "General"}</div>
                <div style={{ fontSize: "0.76rem", color: "#334155", lineHeight: 1.4 }}>{ins.content}</div>
              </div>
            ))
          )}
        </div>
        <button
          onClick={newExploration}
          style={{ marginTop: "auto", border: "2px dashed #cbd5e1", borderRadius: 10, background: "transparent", padding: "0.7rem", fontWeight: 800, fontSize: "0.85rem", cursor: "pointer", fontFamily: "var(--font-display)" }}
        >
          + New Exploration
        </button>
      </aside>

      <section className="tutor-center" style={{ display: "flex", flexDirection: "column", minWidth: 0, minHeight: 0, overflow: "hidden" }}>
        <div style={{ flex: 1, overflowY: "auto", padding: "1.2rem 1.5rem", minHeight: 0 }}>
          <div style={{ maxWidth: 900, margin: "0 auto", display: "flex", flexDirection: "column", gap: "0.8rem" }}>
            {!historyLoaded ? (
              <div style={{ color: "#64748b", fontSize: "0.9rem" }}>Loading conversation...</div>
            ) : messages.map((m, i) => (
              <div
                key={i}
                style={{
                  alignSelf: m.role === "user" ? "flex-end" : "flex-start",
                  maxWidth: "90%",
                  borderRadius: 18,
                  background: m.role === "user" ? "#0f172a" : "#fff",
                  color: m.role === "user" ? "#fff" : "#0f172a",
                  border: m.role === "user" ? "none" : "1px solid #e2e8f0",
                  boxShadow: m.role === "user" ? "0 10px 24px rgba(2, 6, 23, 0.25)" : "0 6px 16px rgba(15, 23, 42, 0.04)",
                  padding: "0.9rem 1rem",
                  fontSize: "1rem",
                  lineHeight: 1.6,
                  overflowWrap: "anywhere",
                }}
              >
                <TutorMarkdown text={m.text || ""} isUser={m.role === "user"} />
              </div>
            ))}
          </div>
        </div>

        <div style={{ borderTop: "1px solid #e2e8f0", background: "#f8f6f5", padding: "0.85rem 1.25rem 1rem", flexShrink: 0 }}>
          <div style={{ maxWidth: 900, margin: "0 auto" }}>
            <div style={{ display: "flex", gap: "0.5rem", background: "#fff", border: "1px solid #e2e8f0", borderRadius: 20, padding: "0.45rem" }}>
              <input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    e.preventDefault();
                    sendMessage(input);
                  }
                }}
                placeholder="Ask me anything about any subject..."
                style={{ flex: 1, border: "none", outline: "none", fontSize: "1rem", padding: "0.6rem 0.8rem", background: "transparent", fontFamily: "var(--font-body)" }}
              />
              <button
                onClick={() => sendMessage(input)}
                disabled={sending || !input.trim()}
                style={{ border: "none", borderRadius: 14, background: "#f45c25", color: "#fff", width: 48, height: 48, cursor: sending || !input.trim() ? "not-allowed" : "pointer", opacity: sending || !input.trim() ? 0.6 : 1 }}
              >
                <span className="material-symbols-outlined">arrow_upward</span>
              </button>
            </div>
          </div>
        </div>
      </section>

      <aside className="tutor-right" style={{ borderLeft: "1px solid #e2e8f0", background: "#fff", padding: "1rem", display: "flex", flexDirection: "column", gap: "0.8rem", minHeight: 0 }}>
        <div style={{ fontSize: "0.68rem", letterSpacing: "0.12em", fontWeight: 800, textTransform: "uppercase", color: "#94a3b8" }}>Matched Concepts</div>
        <div style={{ display: "flex", flexDirection: "column", gap: "0.55rem", overflowY: "auto", minHeight: 0 }}>
          {matchedConcepts.length === 0 ? (
            <div style={{ fontSize: "0.85rem", color: "#64748b" }}>No concept matches yet. Ask a question to start.</div>
          ) : (
            matchedConcepts.map((c, i) => (
              <div key={i} style={{ border: "1px solid #e2e8f0", borderRadius: 10, padding: "0.65rem", background: "#f8fafc" }}>
                <div style={{ fontSize: "0.95rem", fontWeight: 800, marginBottom: "0.25rem" }}>{c.concept}</div>
                <div style={{ display: "flex", gap: "0.4rem", alignItems: "center" }}>
                  <span style={{ fontSize: "0.64rem", textTransform: "uppercase", color: "#64748b", fontWeight: 800 }}>{c.topType?.replace(/_/g, " ") || "Related"}</span>
                  <span style={{ fontSize: "0.64rem", color: "#94a3b8" }}>{c.count} match{c.count === 1 ? "" : "es"}</span>
                </div>
              </div>
            ))
          )}
        </div>
      </aside>

      <style jsx>{`
        .tutor-layout {
          display: grid;
          grid-template-columns: 280px 1fr 300px;
        }
        @media (max-width: 1200px) {
          .tutor-layout {
            grid-template-columns: 250px 1fr 260px;
          }
        }
        @media (max-width: 960px) {
          .tutor-layout {
            grid-template-columns: 1fr;
          }
          .tutor-left,
          .tutor-right {
            display: none !important;
          }
          .tutor-center {
            min-height: calc(100vh - 64px);
          }
        }
      `}</style>
    </div>
  );
}
