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
        let text = children;

        // Replace display math ($$...$$) first
        text = text.replace(/\$\$([\s\S]*?)\$\$/g, (_match, tex) => {
            try {
                return katex.renderToString(tex.trim(), {
                    displayMode: true,
                    throwOnError: false,
                });
            } catch {
                return `$$${tex}$$`;
            }
        });

        // Replace inline math ($...$)
        text = text.replace(/\$([^$\n]+?)\$/g, (_match, tex) => {
            try {
                return katex.renderToString(tex.trim(), {
                    displayMode: false,
                    throwOnError: false,
                });
            } catch {
                return `$${tex}$`;
            }
        });

        return text;
    }, [children]);

    return (
        <Tag
            className={className}
            dangerouslySetInnerHTML={{ __html: html }}
            {...props}
        />
    );
}
