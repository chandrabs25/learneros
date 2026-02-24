"use client";

import { useMemo } from "react";
import katex from "katex";
import "katex/dist/katex.min.css";

/**
 * Renders text with inline LaTeX ($...$) and display LaTeX ($$...$$).
 * Replaces LaTeX expressions with rendered HTML using KaTeX.
 */
interface LatexTextProps extends React.HTMLAttributes<HTMLElement> {
    children: string;
    as?: "span" | "p" | "div" | "h1" | "h2" | "h3" | "h4" | "strong" | "li";
}

export default function LatexText({
    children,
    className,
    as: Tag = "span",
    ...props
}: LatexTextProps) {
    const html = useMemo(() => {
        if (!children) return "";
        const escapeHtml = (value: string) =>
            value
                .replaceAll("&", "&amp;")
                .replaceAll("<", "&lt;")
                .replaceAll(">", "&gt;")
                .replaceAll('"', "&quot;")
                .replaceAll("'", "&#39;");

        const regex = /(\$\$[\s\S]*?\$\$|\$[^$\n]+?\$)/g;
        const parts = children.split(regex).filter((part) => part.length > 0);
        const rendered: string[] = [];

        for (const part of parts) {
            const isDisplay = part.startsWith("$$") && part.endsWith("$$");
            const isInline = part.startsWith("$") && part.endsWith("$") && !isDisplay;
            if (isDisplay || isInline) {
                const tex = isDisplay ? part.slice(2, -2).trim() : part.slice(1, -1).trim();
                try {
                    rendered.push(
                        katex.renderToString(tex, {
                            displayMode: isDisplay,
                            throwOnError: false,
                        }),
                    );
                } catch {
                    rendered.push(escapeHtml(part));
                }
                continue;
            }
            rendered.push(escapeHtml(part));
        }

        return rendered.join("");
    }, [children]);

    return (
        <Tag
            className={className}
            dangerouslySetInnerHTML={{ __html: html }}
            {...props}
        />
    );
}
