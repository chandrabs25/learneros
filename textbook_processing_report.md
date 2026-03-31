# Textbook Processing Report

This report explains how the repository extracts textbook structure from PDFs, cleans and merges the output, handles failures, creates concept prerequisites, normalizes references, and deduplicates concepts.

## 1. End-to-end flow

The implemented pipeline is not a single script. It is a staged flow:

1. `extract/pdf_to_json.py`
   Extracts one chapter PDF into structured JSON by processing the PDF page images in small batches.
2. `extract/enrich_json.py`
   Adds chapter summaries and section prerequisite lists when they are missing.
3. `extract/enrich_concepts.py`
   Ensures each chapter has a minimum number of concept prerequisites by adding cross-chapter concepts.
4. `extract/normalize_json.py`
   Canonicalizes concept refs, section refs, and exercise test refs.
5. Subject-specific cleanup
   `extract/dedup_physics_concepts.py`, `extract/dedup_biology_concepts.py`, and chemistry normalization scripts consolidate duplicate concepts.
6. Database sync
   `db/seed_all.sh` seeds JSON into Neo4j, and `db/update_merged_concepts.py` reconciles graph nodes after concept merges.

There are also batch runner scripts like `extract/run_all.sh`, `extract/run_bio11.sh`, and `extract/run_chem12.sh` that repeatedly call the extractor with `--resume`.

## 2. Structure extraction from textbooks

### Source input

The extractor starts from chapter PDFs, not pre-extracted text. In `extract/pdf_to_json.py`, each PDF page is rendered to a PNG using PyMuPDF at `PAGE_DPI = 200`. This means the primary extraction path is vision-based, not OCR text parsing.

### Page batching strategy

Pages are processed in batches of 3 images at a time. For each batch, the script builds a prompt and sends:

- a continuity snapshot from prior batches
- the current page images
- a JSON schema describing the expected output

This keeps context local while still allowing continuity across page boundaries.

### Extracted structure

For each batch, the LLM is asked to return:

- `chapter_title`
- `sections`
- `subsections`
- `worked_examples`
- `diagrams`
- `tables`
- `exercises`
- `prerequisites`

The intended teaching granularity is the subsection. The prompt explicitly asks the model to split material into atomic teaching units such as:

- explanations
- derivation steps
- definitions
- laws
- theorems
- experiments
- applications

The extractor also instructs the model to:

- preserve numbered sections
- continue a section if a page batch begins in the middle of one
- continue subsection ordering across page batches
- combine content spanning pages inside a batch
- ignore objectives, headers, footers, QR codes, and reprint notices
- read multi-column layouts in left-to-right reading order

### Continuity snapshot

The continuity mechanism is implemented in `build_snapshot()`. It carries forward:

- section numbers/titles already seen
- the last section and subsection
- trailing incomplete text marked with `[CONTINUES]`
- skipped-page warnings
- the last extracted exercise and incomplete exercise text

This snapshot is the main reason page-local extraction can still maintain chapter-level structure.

### Chapter title extraction

Chapter titles are extracted separately from page structure. The extractor first tries to parse the first PDF page text directly. If that fails, it falls back to a hardcoded NCERT `(subject, grade, chapter)` title map.

## 3. Cleaning and repair

Cleaning happens at multiple points rather than in one dedicated cleanup pass.

### During LLM response handling

`call_gemini()` performs light repair when model output is malformed:

- closes unterminated JSON strings
- removes a trailing comma
- appends missing closing brackets/braces
- retries on malformed JSON and transient API failures

This is an important first-stage cleanup because page extraction can continue without manual intervention for common truncation cases.

### During merge

`merge_chunks()` cleans page-level outputs while assembling the final chapter:

- merges subsections that were split across page boundaries
- stitches text ending with `[CONTINUES]`
- merges associated worked examples, diagrams, and tables from continued chunks
- combines same-titled or near-identical subsections using `_titles_match()`
- re-numbers subsection `order` fields sequentially within each section
- deduplicates section prerequisites
- deduplicates exercises by exercise number
- defaults invalid `content_type` values to `explanation`
- defaults invalid `exercise_type` values to `conceptual`

### During normalization

`extract/normalize_json.py` is the main canonical cleanup pass before database seeding. It:

- normalizes concept refs to `concept:snake_case`
- normalizes section refs to full IDs such as `ncert:physics:11:1:1.1`
- converts malformed colon-separated section suffixes like `7:1` into `7.1`
- drops unparseable section refs such as bare text like `9.2 Alkanes`
- deduplicates prerequisite refs after normalization
- normalizes exercise `tests` refs without corrupting section refs

### Targeted cleanup scripts

There are also targeted repair scripts for specific error classes:

- `extract/fix_section_refs.py`
  Converts bad exercise test refs like `concept:ncert_physics_11_1_1_1` into proper section IDs.
- subject-specific `fix_*.py` scripts
  These appear to patch chapter-specific extraction issues.

## 4. Merging behavior

Merging is a core part of the architecture, not an afterthought.

### Why merging is needed

Because extraction happens page-batch by page-batch, sections and subsections frequently span multiple batches. The system therefore merges programmatically in Python instead of trusting the model to return one perfect chapter object.

### Merge rules

The merge logic in `merge_chunks()` works as follows:

- sections are keyed by section number
- if a section is first seen, it is added to `merged_sections`
- if the section already exists, new subsections are appended
- if the last existing subsection ends with `[CONTINUES]`, the first subsection of the next chunk is stitched onto it
- if consecutive subsection titles match exactly, nearly match, or one contains the other, they are merged
- prerequisites are combined and deduplicated
- exercise items from all chunks are gathered into one list, continued exercise statements are stitched, then items are deduplicated by number

### Result

The final merged object is chapter-level JSON that is then validated against the Pydantic schema in `db/models.py`.

## 5. Fallback for failures

The pipeline has several fallback layers.

### Resume fallback

The extractor writes a `.progress.json` file before merge/validation. On a rerun with `--resume`, previously extracted chunks are loaded and later batches are skipped. This prevents a full restart after a partial failure.

Batch runner scripts such as `extract/run_all.sh` and `extract/run_bio11.sh` add another outer fallback:

- retry the chapter up to 3 times
- wait 300 seconds between attempts
- continue with the next chapter if retries are exhausted

### Chapter-title fallback

If title extraction from the PDF fails, the extractor falls back to the hardcoded NCERT chapter title map. If the merged result still has no chapter title, it derives one from the first section title.

### JSON repair fallback

If the LLM returns truncated JSON, `_repair_json()` attempts to repair it before the batch is considered failed.

### RECITATION fallback

The most explicit failure strategy is for Gemini RECITATION blocking:

1. First attempt: extract with the normal detailed prompt.
2. If blocked: retry with a summarize-and-rephrase prompt.
3. If blocked again: skip the page range and log it to `data/recitation_skipped.md`.
4. Insert a placeholder chunk carrying:
   - the last known section number/title when possible
   - a synthetic skipped subsection
   - `[CONTINUES]` so later continuity still works

This is a particularly thoughtful fallback because it preserves structural continuity even when actual content is unavailable.

### Validation fallback

If final Pydantic validation fails, the merged chapter is saved as `.raw.json` for debugging rather than being lost.

## 6. Concept creation

Concept creation in this repo mostly means generating prerequisite concept references, not building rich concept definitions.

### Section-level prerequisite generation

`extract/enrich_json.py` asks Gemini to infer prerequisites for each section. It can return two kinds of prerequisites:

- `type = "section"` for dependencies within the same chapter
- `type = "concept"` for dependencies from other chapters or subjects

This pass is selective:

- it mainly targets sections missing prerequisites
- it skips pseudo-sections like `Summary`, `Points to Ponder`, `Answers`, and `Exercises`

### Minimum concept threshold

`extract/enrich_concepts.py` enforces a minimum number of concept prerequisites per chapter (`MIN_CONCEPTS = 5`).

If a chapter has too few concept prerequisites:

- it builds a section overview
- lists existing concepts
- asks Gemini for additional cross-chapter foundational concepts
- maps each suggested concept to a target section
- falls back to the first real content section if the suggested section does not exist

This script is effectively a concept backfill stage to improve graph density and prerequisite coverage.

## 7. Normalizing

Normalization happens in both the main merge function and the dedicated normalization script.

### In `merge_chunks()`

The extractor already performs first-pass normalization:

- concept refs are converted to `concept:snake_case`
- bare section numbers are expanded to full IDs with the current chapter prefix
- same-chapter refs with colon-separated suffixes are converted to dotted suffixes
- exercise `tests` are normalized as concept refs

### In `extract/normalize_json.py`

The repository then runs a broader idempotent normalization pass over all chapter JSON files. This is the canonical pre-seeding normalizer.

Its goals are:

- consistent concept naming
- consistent section reference formatting
- dropping invalid refs introduced by the model
- deduplicating repeated refs

### Chemistry-specific normalization

Chemistry has additional standalone normalization scripts:

- `scripts/normalize_chemistry_concepts.py`
- `scripts/normalize_chemistry_concepts_v2.py`

These are more aggressive than the generic normalizer. They roll up many narrow chemistry concepts into broader canonical names and align chemistry naming with conventions already used in physics and other subjects.

Notably, these chemistry scripts are not wired into `db/seed_all.sh`, so they appear to be optional/manual cleanup stages rather than part of the always-on path.

## 8. Deduplication

Deduplication is handled at several levels.

### Prerequisite and exercise deduplication

In both merge and normalization passes, prerequisite refs and exercise test refs are deduplicated using `seen` sets.

### Subject-level concept deduplication

Physics and biology each have explicit concept merge maps.

`extract/dedup_physics_concepts.py` merges near-duplicates such as:

- `concept:amperes_circuital_law` -> `concept:amperes_law`
- `concept:work_and_energy` -> `concept:work`
- `concept:linear_momentum` -> `concept:momentum`

`extract/dedup_biology_concepts.py` does two things:

- merges verbose or overlapping concept names into canonical ones
- removes low-value or overly generic concepts entirely

Examples include:

- `concept:eukaryotic_cell_structure` -> `concept:cell_structure`
- `concept:pregnancy_and_embryonic_development` -> `concept:embryonic_development`
- removing generic concepts like `concept:zygote` and `concept:states_of_matter`

### Database-level dedup sync

After JSON files are cleaned, `db/update_merged_concepts.py` updates Neo4j by:

- moving `REQUIRES` relationships from old concept nodes to canonical nodes
- moving `TESTS` relationships likewise
- deleting old merged concept nodes
- removing fully deleted concept nodes
- cleaning orphaned concept nodes with no relationships

This matters because file-level dedup alone would not clean an already-seeded graph.

## 9. What is the actual “core” pipeline vs optional cleanup

### Core path

The consistently implemented core path is:

1. extract pages from PDF
2. batch vision extraction with continuity snapshot
3. merge page chunks
4. validate against Pydantic schema
5. save chapter JSON
6. normalize JSON
7. seed into Neo4j

### Enrichment path

These are content-improving but not strictly required for a valid chapter JSON:

- `extract/enrich_json.py`
- `extract/enrich_concepts.py`

### Optional/manual cleanup path

These appear to be maintenance or one-time cleanup tools:

- `extract/dedup_physics_concepts.py`
- `extract/dedup_biology_concepts.py`
- `scripts/normalize_chemistry_concepts.py`
- `scripts/normalize_chemistry_concepts_v2.py`
- `extract/fix_section_refs.py`
- chapter-specific `fix_*.py` scripts

## 10. Summary

The repository extracts textbook structure using a multimodal page-batch pipeline with continuity snapshots, then merges the batch outputs programmatically into a validated chapter JSON. Cleaning is distributed across JSON repair, merge-time stitching, normalization, and targeted fix scripts. Failure handling is robust: retries, progress resume, RECITATION fallback, skipped-page placeholders, and raw debug dumps all help preserve work. Concept creation is implemented as prerequisite generation and concept backfilling, while normalization and deduplication standardize references and collapse noisy concept variants before and after graph ingestion.

