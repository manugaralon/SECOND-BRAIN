# Phase 1: KB Schema + Personal Context Seed - Context

**Gathered:** 2026-04-10
**Status:** Ready for planning

<domain>
## Phase Boundary

Lock the knowledge schema and create 2-3 minimal personal context entries that validate the schema and give the oracle day-1 personal context. No comprehensive manual authoring — personal knowledge enters the same way all other knowledge does: via sources fed to the processor. Phase 1 only proves the schema works.

</domain>

<decisions>
## Implementation Decisions

### Schema — required fields (max 6)

```yaml
concept: "name of the atomic concept"
domain: "fisioterapia | ia | finanzas | trading | esoterismo | psicología | deportes | personal"
confidence: 0.7          # float 0.0–1.0
summary: "One sentence describing what this entry asserts"
sources:
  - note: "notes/slug.md"   # or url: "https://..."
    date: "2026-04-10"
last_updated: "2026-04-10"
```

### Schema — optional fields

```yaml
contradicts:
  - concept: "other-concept"
    detail: "what specifically contradicts"
extends:
  - concept: "parent-concept"
gaps:
  - "what is still unknown or unverified"
```

Rationale: `contradicts`, `extends`, `gaps` are optional — most entries won't have them on creation. Forcing empty arrays pollutes files and adds noise to LLM prompts.

### Confidence scale semantics

| Value | Meaning |
|-------|---------|
| 0.9+ | Multiple independent sources agree, no contradictions |
| 0.7–0.9 | Single high-quality source, or multiple weak sources agreeing |
| 0.5–0.7 | Contested, single influencer source, or unverified claim |
| <0.5 | Explicitly contradicted or speculative |

### Directory structure

- `kb/concepts/` — all domain knowledge, flat
- `kb/personal/` — personal context entries only
- No subdirectories by domain until corpus exceeds ~100 entries
- `domain` frontmatter field handles filtering — filesystem structure does not

### Slug naming convention

Kebab-case of concept name. No domain prefix. No UUID.

Examples: `escoliosis-lumbar-diagnostico.md`, `pies-planos-tipo.md`, `prompting-chain-of-thought.md`

When a concept spans multiple atomic aspects, use a qualifier suffix:
`escoliosis-lumbar-restricciones.md`, `escoliosis-lumbar-ejercicios-contraindicados.md`

### Personal context entries for Phase 1

Granularity: **multiple atomic entries per condition** — not one monolithic entry per condition.

Entries to create (minimal demo, not exhaustive):
- `kb/personal/escoliosis-lumbar-diagnostico.md` — what the condition is, severity, curve type if known
- `kb/personal/pies-planos-tipo.md` — type of flat foot, pronation pattern
- `kb/personal/perfil-fisico-general.md` — height, weight, activity level, sports history
- One more from: situación actual / objetivos físicos actuales

Content approach: write what Manuel already knows. Incomplete is fine — the processor enriches entries when sources arrive. Phase 1 is not about completeness, it's about schema validation.

### Flow clarification (locked)

Manuel feeds sources in any format → processor extracts and structures → KB grows automatically. Personal context is not a pre-defined profile — it enters the KB the same way all other knowledge does. Phase 1 demo entries are the minimum to prove the schema works and give the oracle something to work with on day 1.

### Claude's Discretion

- Exact body format of entries (prose vs bullet list below frontmatter)
- Whether `kb/INDEX.md` is auto-generated or hand-maintained in Phase 1

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project requirements
- `.planning/REQUIREMENTS.md` — KB-02 (schema standard), KB-03 (personal context as knowledge)
- `.planning/ROADMAP.md` §Phase 1 — Success criteria: schema.md exists, kb/personal/ has ≥3 entries, INDEX.md template exists, python-frontmatter parses without error

### Existing pipeline (read-only — do not modify)
- `/home/manuel/Desktop/PROJECTS/IMPENV/pipeline/transcribe.py` — existing ingest pipeline; notes output format is the upstream input to this KB
- `/home/manuel/Desktop/PROJECTS/IMPENV/pipeline/notes/` — sample notes to understand what upstream data looks like

No external specs — requirements fully captured in decisions above.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- None in SECONDBRAIN repo — project starts from scratch in Phase 1

### Established Patterns
- Upstream notes use YAML frontmatter (title, url, topic, type, author, processed_date, tags) — the KB schema is a different, richer abstraction above these notes
- `python-frontmatter` is the validation tool specified in Phase 1 success criteria

### Integration Points
- Phase 1 outputs (`schema.md`, `kb/personal/*.md`, `kb/INDEX.md`) are the inputs Phase 2's `process.py` writes to
- No code written in Phase 1 — pure schema design and manual authoring

</code_context>

<specifics>
## Specific Ideas

- Personal context entries are atomic by aspect, not one blob per condition (e.g., `escoliosis-lumbar-diagnostico.md` separate from `escoliosis-lumbar-restricciones.md`)
- The oracle should be able to load all of `kb/personal/` in context without needing to know which entry has what — keep entries small

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 01-kb-schema-personal-context-seed*
*Context gathered: 2026-04-10*
