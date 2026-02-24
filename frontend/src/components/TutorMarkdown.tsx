"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";
import "katex/dist/katex.min.css";

type TutorMarkdownProps = {
  text: string;
  compact?: boolean;
  isUser?: boolean;
};

export default function TutorMarkdown({ text, compact = false, isUser = false }: TutorMarkdownProps) {
  const blockGap = compact ? "0.45rem" : "0.65rem";
  const fontSize = compact ? "0.84rem" : "0.98rem";
  const borderColor = isUser ? "rgba(255,255,255,0.22)" : "#cbd5e1";
  const codeBg = isUser ? "rgba(255,255,255,0.16)" : "rgba(148,163,184,0.2)";
  const preBg = isUser ? "rgba(2,6,23,0.32)" : "rgba(15,23,42,0.08)";
  const tableBg = isUser ? "rgba(2,6,23,0.32)" : "#fff";
  const tableHeaderBg = isUser ? "rgba(2,6,23,0.45)" : "#f8fafc";
  const textColor = isUser ? "#fff" : "#0f172a";

  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm, remarkMath]}
      rehypePlugins={[rehypeKatex]}
      components={{
        p: ({ children }) => <p style={{ margin: `0 0 ${blockGap} 0`, fontSize, color: textColor }}>{children}</p>,
        h1: ({ children }) => <h1 style={{ margin: `0 0 ${blockGap} 0`, fontSize: compact ? "1rem" : "1.1rem", fontWeight: 800 }}>{children}</h1>,
        h2: ({ children }) => <h2 style={{ margin: `0 0 ${blockGap} 0`, fontSize: compact ? "0.95rem" : "1.05rem", fontWeight: 800 }}>{children}</h2>,
        h3: ({ children }) => <h3 style={{ margin: `0 0 ${blockGap} 0`, fontSize: compact ? "0.9rem" : "1rem", fontWeight: 800 }}>{children}</h3>,
        ul: ({ children }) => <ul style={{ margin: `0.2rem 0 ${blockGap} 1.2rem`, fontSize, color: textColor }}>{children}</ul>,
        ol: ({ children }) => <ol style={{ margin: `0.2rem 0 ${blockGap} 1.2rem`, fontSize, color: textColor }}>{children}</ol>,
        li: ({ children }) => <li style={{ marginBottom: compact ? "0.2rem" : "0.3rem" }}>{children}</li>,
        code: ({ children }) => (
          <code style={{ background: codeBg, borderRadius: 6, padding: "0.1rem 0.3rem", border: `1px solid ${borderColor}` }}>
            {children}
          </code>
        ),
        pre: ({ children }) => (
          <pre
            style={{
              background: preBg,
              borderRadius: 10,
              padding: compact ? "0.6rem" : "0.75rem",
              overflowX: "auto",
              border: `1px solid ${borderColor}`,
              marginBottom: blockGap,
            }}
          >
            {children}
          </pre>
        ),
        table: ({ children }) => (
          <div style={{ overflowX: "auto", border: `1px solid ${borderColor}`, borderRadius: 8, background: tableBg, marginBottom: blockGap }}>
            <table style={{ borderCollapse: "collapse", minWidth: "100%", fontSize, color: textColor }}>{children}</table>
          </div>
        ),
        th: ({ children }) => (
          <th
            style={{
              textAlign: "left",
              padding: compact ? "0.35rem 0.45rem" : "0.42rem 0.5rem",
              borderBottom: `1px solid ${borderColor}`,
              background: tableHeaderBg,
              fontWeight: 700,
              whiteSpace: "nowrap",
            }}
          >
            {children}
          </th>
        ),
        td: ({ children }) => (
          <td style={{ padding: compact ? "0.32rem 0.45rem" : "0.38rem 0.5rem", borderTop: `1px solid ${borderColor}`, verticalAlign: "top" }}>
            {children}
          </td>
        ),
      }}
    >
      {text || ""}
    </ReactMarkdown>
  );
}

