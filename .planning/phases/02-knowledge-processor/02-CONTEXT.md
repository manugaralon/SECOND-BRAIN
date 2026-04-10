# Phase 2: Knowledge Processor - Context

**Gathered:** 2026-04-10
**Status:** Ready for planning

<domain>
## Phase Boundary

Build `process.py` — a script that reads upstream notes (`notes/*.md`, output of `transcribe.py`) and converts them into atomic KB entries in `kb/concepts/`. Handles idempotency, contradiction detection, and schema validation. The upstream pipeline (`transcribe.py`) is read-only and must not be modified.

</domain>

<decisions>
## Implementation Decisions

### Extraction granularity
- **Atomic per concept** — one KB entry per concept extracted, not one per source note
- A carousel with 6 patterns → 6 separate `kb/concepts/*.md` entries
- One note can yield 1 or N entries depending on how many distinct concepts it contains
- Each entry's `sources` field points back to the originating note slug

### Manual intervention on low-confidence extraction
- When the processor cannot confidently identify a clean concept (vague content, ambiguous domain, insufficient signal), it **pauses and asks for confirmation** before writing
- Low-confidence threshold is Claude's discretion (suggested: < 0.5)
- Interactive prompt shows the proposed entry and asks: write / skip / edit concept name
- Non-interactive mode flag (`--no-confirm`) available for batch runs where pausing is not wanted — logs uncertain entries instead

### Claude's Discretion
- Idempotency mechanism: `processed.log` file tracking processed note slugs (simpler than frontmatter mutation on source notes)
- Contradiction detection: LLM comparison of new entry against existing `kb/concepts/*.md` entries with same domain — if semantic conflict detected, populate `contradicts` field on new entry and log
- CLI structure: `process.py ingest <file>`, `process.py ingest --all`, `process.py lint`
- Log format: plain text or JSONL, one line per operation
- Confidence threshold value for "low confidence" pause
- Whether `kb/INDEX.md` is updated by process.py or kept manual in Phase 2

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### KB schema (output contract)
- `schema.md` — canonical KB entry schema: 6 required fields, 3 optional groups, confidence scale, slug naming convention
- `kb/personal/escoliosis-lumbar-diagnostico.md` — example of a correctly-structured entry

### Project requirements
- `.planning/REQUIREMENTS.md` — KB-01 (ingest links → notes), KB-04 (contradiction detection), KB-07 (reproducible ingest flow)
- `.planning/ROADMAP.md` §Phase 2 — success criteria: idempotency, contradiction flagging, lint command, all 14+ notes processed

### Upstream pipeline (read-only — do not modify)
- `/home/manuel/Desktop/PROJECTS/IMPENV/pipeline/transcribe.py` — produces the notes that process.py reads
- `/home/manuel/Desktop/PROJECTS/IMPENV/pipeline/notes/` — 14 sample notes; read these to understand upstream format before planning tasks

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `schema.md` — the output contract; process.py must write entries that pass `python-frontmatter` validation against this schema
- `kb/personal/*.md` — 4 existing entries; useful as reference for target format and body style

### Established Patterns
- Upstream notes format: YAML frontmatter (title, url, topic, type, author, images, processed_date, tags) + markdown body with extracted content per image/section
- Slug pattern: kebab-case of concept name, no domain prefix, qualifier suffix for multi-aspect concepts
- `domain` field handles filtering — no filesystem subdirectories

### Integration Points
- `process.py` reads from `/home/manuel/Desktop/PROJECTS/IMPENV/pipeline/notes/` (or a configured path)
- `process.py` writes to `kb/concepts/`
- `processed.log` lives at project root or `kb/`
- `kb/INDEX.md` may need updating (Claude's discretion whether process.py does this in Phase 2)

</code_context>

<specifics>
## Specific Ideas

- One note → N atomic entries (not 1:1 mapping). The processor must extract ALL distinct concepts from a note, not just the "main" one.
- Interactive confirmation flow when confidence is low — show proposed entry, offer write/skip/rename.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 02-knowledge-processor*
*Context gathered: 2026-04-10*
