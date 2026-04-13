# Roadmap: Second Brain — El Oraculo

## Overview

The system is built in three executable phases plus one deferred phase. Phase 1 locks the knowledge schema and seeds personal context manually — no code, pure design and authoring. Phase 2 builds the knowledge processor (`process.py`) that converts existing `notes/*.md` into a structured `kb/`. Phase 3 writes the `CLAUDE.md` oracle contract that turns Claude Code into a personalized query interface. Phase 4 (semantic search via ChromaDB) is deferred until the corpus exceeds ~100 concepts — the threshold where plain file reads become insufficient.

## Phases

- [x] **Phase 1: KB Schema + Personal Context Seed** - Lock the knowledge schema and author personal context entries manually before any LLM writes to the KB (completed 2026-04-10)
- [x] **Phase 2: Knowledge Processor** - Build `process.py` that converts `notes/*.md` → atomic `kb/*.md` with contradiction detection and idempotency (completed 2026-04-11)
- [x] **Phase 3: Oracle Interface** - Write the `CLAUDE.md` that turns Claude Code into the oracle: domain filtering, contradiction surfacing, gap detection, personalized synthesis (completed 2026-04-13)
- [ ] **Phase 4: Semantic Search** - Add ChromaDB vector index when corpus exceeds ~100 concepts (deferred — plan only when threshold is reached)

## Phase Details

### Phase 1: KB Schema + Personal Context Seed
**Goal**: The knowledge schema is locked, personal context lives in the KB, and no LLM can write entries until the foundation is stable
**Depends on**: Nothing (first phase)
**Requirements**: KB-02, KB-03
**Success Criteria** (what must be TRUE):
  1. `schema.md` exists with all field definitions, types, and required/optional status — max 6 required fields
  2. `kb/personal/` contains at least escoliosis, pies planos, and one additional context entry, each following the canonical schema
  3. `kb/INDEX.md` template exists with entry format (slug + domain + one-sentence summary + path) ready for processor output
  4. Running `python-frontmatter` against any personal entry parses without error — schema is valid YAML
**Plans:** 1/1 plans complete

Plans:
- [x] 01-01-PLAN.md — Lock schema and author personal context seed entries

### Phase 2: Knowledge Processor
**Goal**: `process.py` can convert all 14+ existing notes into structured KB entries, idempotently, with contradictions flagged and a processing log emitted
**Depends on**: Phase 1
**Requirements**: KB-01, KB-04, KB-07
**Success Criteria** (what must be TRUE):
  1. `python process.py ingest notes/some-note.md` creates one or more `kb/concepts/*.md` files that pass schema validation
  2. Running the same command twice on the same note produces no duplicate entries (`processed.log` or frontmatter flag prevents re-processing)
  3. When a note contradicts an existing KB entry, the `contradicts` field is populated on at least one of the two entries and the processing log reports the conflict
  4. All 14+ existing notes are processed and result in a non-empty `kb/concepts/` directory
  5. `python process.py lint` checks all KB entries against the canonical schema and reports any violations
**Plans**: 3/3 plans complete

Plans:
- [x] 02-01-PLAN.md — TDD scaffold and core ingest pipeline
- [x] 02-02-PLAN.md — Idempotency and lint subcommand
- [x] 02-03-PLAN.md — Contradiction detection and batch ingest

### Phase 3: Oracle Interface
**Goal**: Claude Code can answer personalized questions by reading the KB, applying personal context automatically, surfacing contradictions and gaps without manual setup per session
**Depends on**: Phase 2
**Requirements**: KB-05, KB-06
**Success Criteria** (what must be TRUE):
  1. Asking "que ejercicios puedo hacer para la escoliosis" in a fresh Claude Code session returns an answer that explicitly references personal context entries (escoliosis, pies planos) without the user providing them
  2. When querying a domain with few entries, the oracle states "sobre X hay N entradas — cobertura escasa" unprompted
  3. When querying a topic where two KB entries contradict each other, the oracle surfaces both positions and does not silently resolve them
  4. The oracle declares which domains it consulted in every substantive answer
  5. A fresh session requires zero manual setup — reading `CLAUDE.md` is sufficient for Claude to navigate the full KB
**Plans:** 2/2 plans complete

Plans:
- [ ] 03-01-PLAN.md — Backfill INDEX.md with all KB entries + rebuild-index subcommand
- [ ] 03-02-PLAN.md — Write CLAUDE.md oracle contract + human verification

### Phase 4: Semantic Search
**Goal**: Vector-based retrieval replaces full-KB reads when the corpus exceeds ~100 concepts
**Depends on**: Phase 3, corpus > 100 entries
**Requirements**: None (v2 scope — deferred)
**Success Criteria** (what must be TRUE):
  1. ChromaDB index is populated from `kb/*.md` and stays in sync when entries are added or updated
  2. Semantic queries return more relevant results than keyword/full-read approach on corpus of 100+ entries
  3. The canonical `kb/*.md` layer is unchanged — vector index is additive, not a replacement
**Plans**: TBD — plan only when corpus threshold is reached

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. KB Schema + Personal Context Seed | 1/1 | Complete   | 2026-04-10 |
| 2. Knowledge Processor | 3/3 | Complete   | 2026-04-12 |
| 3. Oracle Interface | 2/2 | Complete   | 2026-04-13 |
| 4. Semantic Search | 0/? | Deferred | - |
