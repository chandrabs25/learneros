# LearnerOS backend architecture DOCX template contract

## Reference

- Path: `/Users/srichandrasamanapalli/code/AI TUTOR/learneros/backend/docs/LearnerOS_Backend_Architecture.docx`
- SHA-256: `e4d6593a859e22ffaae42fce6de83bd9169a9c9153e867ec74972dec987b6a56`
- Pages: 14 rendered pages
- Sections: 1
- Render evidence: `tmp/docs/backend-architecture/deepened-render-5/`
- Accessibility evidence: `tmp/docs/backend-architecture/deepened-a11y.json` (0 high, 0 medium, 0 low findings)
- Style evidence: `tmp/docs/backend-architecture/reference-style-evidence.json`

## Page system

- US Letter portrait, one section.
- Margins: left 0.78 in, right 0.78 in, top 0.72 in, bottom 0.70 in.
- Header and footer are distinct document parts; no first-page or odd/even variants.
- Footer contains the static label and a page-number field. Header contains the uppercase report label.

## Typography and color

- Primary type: Aptos; code/configuration blocks: Consolas.
- Title: Word `Title` style with large dark-navy type and a blue rule below.
- Main sections: `Heading 1`, dark navy, numbered in text.
- Subsections: `Heading 2`, teal.
- Body: `Normal`, dark blue-gray, readable report spacing.
- Lists: real `List Bullet` paragraphs with hanging alignment.
- Table headers: dark navy fill, white bold uppercase text.
- Table bodies: alternating white and very-light-blue fills with thin blue-gray borders.
- Callouts reuse the retained blue, yellow, or red bordered/fill patterns.

## Components and flow

- Page 1 combines title block, metadata table, reading-guide callout, contents, and the beginning of Section 1.
- Pages 2-14 use the same header/footer system and continuous report flow.
- The report contains 15 numbered sections, 30 tables, code/configuration callouts, and operational note boxes.
- Tables use the retained explicit grid and cell geometry; row heights must remain automatic.

## Editable slots for this update

- Cover subtitle, status/reading-guide wording, and Contents item 12.
- Assessment-related text in Sections 1, 2, 3, 5, 6, 7, 9, 12, and 15.
- Current model-routing, structured-output, insight-convergence, and privacy-safe telemetry text in Sections 1, 6, 7, 9, 12, 13, 15, and 16.
- Existing assessment rows in request-lifecycle, route, prompt-context, cache, caveat, and source-file tables.
- Section 12 is repurposed in place from telemetry/eval-tooling detail to current assessment context and concept-fallback behavior.
- Existing list, table, code-block, and callout components are reused; no new page system or visual language is introduced.

## Preserve-only package areas

- Section properties, theme, styles, numbering definitions, headers, footers, page fields, relationships, and document metadata.
- All non-assessment architecture sections unless a short accuracy correction is required by the current assessment routing behavior.
- Table geometry, cell margins, fills, borders, and recurring header/footer furniture.

## Fidelity gates

- Reference file remains unchanged until the updated draft passes render QA.
- Final remains US Letter portrait with one section and recognizable retained styling.
- All final pages must be inspected at 100 percent zoom with no clipping, overlap, broken tables, or orphaned headings.
- The updated document must explicitly state: target-subsection primary content, full-section reference context, direct-section concept scope, chapter fallback for sections without direct concepts, empty-insight behavior when no valid candidates exist, and concepts excluded from question generation.
- The updated document must state that all text, JSON, embedding, tutor, and evaluation paths use Fireworks; image/handwriting evaluation uses the separate Fireworks vision model.
- The updated document must describe four-option JSON-schema-constrained MCQ output, bounded completion tokens, durable assessment-status polling, uncached current-subsection insight reads, and sanitized LLM failure telemetry.
- The updated document must identify `services/learner_evidence.py` as the deep persistence module. It transactionally creates durable Neo4j `LearnerEvidenceJob` records before reporting queued, uses indexed lock-before-predicate claim tokens and leases across workers, recovers expired or unaccounted jobs, uses idempotent insight identities, and internally owns reconciliation, embedding, Neo4j persistence, retry/dead-letter handling, cache invalidation, and atomic Assessment Attempt result accounting.
- Unrelated eval/export/promotion/observability scripts are excluded from the updated source list and behavioral claims.
