# Domain documentation

LearnerOS uses a single-context domain-document layout.

Before exploring or changing the codebase:

1. Read the root `CONTEXT.md` glossary.
2. Read relevant decisions under `docs/adr/`.
3. Use the glossary's exact domain terms in code, tests, issues, and documentation.
4. Surface any conflict with an ADR instead of silently overriding it.

If a required concept is missing, update `CONTEXT.md` only when the term represents a durable domain distinction. Record decisions that constrain future architecture as ADRs.
