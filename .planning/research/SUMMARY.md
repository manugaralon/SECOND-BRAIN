# Research Summary: Second Brain — El Oráculo

**Project:** Second Brain — El Oráculo
**Domain:** Personal adaptive knowledge oracle (PKM + LLM synthesis + personalized retrieval)
**Researched:** 2026-04-08
**Confidence:** HIGH

## Executive Summary

This is a personal knowledge oracle built on top of an existing content ingestion pipeline. The pattern is well-validated — Karpathy published the exact architecture in April 2026: LLM-maintained atomic `.md` files as a structured wiki, queried by Claude Code without embeddings or vector infra. The recommended approach is to build the missing layer between the existing `transcribe.py` output (`notes/*.md`) and a queryable knowledge base (`kb/*.md`). A `process.py` script uses `instructor` + Groq to extract atomic concepts from raw notes into structured entries, and a `CLAUDE.md` at the repo root turns Claude Code into the oracle interface. No new infrastructure beyond Python + Groq is needed for the MVP.

The critical risk is not technical — it is epistemic: the LLM will embed hallucinations as permanent KB facts, and the oracle will cite them as verified. The prevention is a mandatory `confianza` field (baja/media/alta) that defaults to `baja` on ingest and is never promoted automatically. The second major risk is the schema growing to 12+ fields before any content exists, creating ingest friction that kills the project. The schema must be locked at 6 required fields before writing a single entry.

The pipeline already works (14/14 posts ingested). The entire scope of this project is: schema design + personal context seed, knowledge processor (process.py), and oracle interface (CLAUDE.md). Vector search and web UI are explicitly out of scope until the corpus exceeds 100 concepts.

## Key Findings

### Recommended Stack

The existing pipeline (`yt-dlp` + `groq` SDK) is untouched. The new layer adds three dependencies: `instructor` v1.14.5 for structured LLM extraction (schema-first, Pydantic-native, officially integrates with Groq's `json_schema` + `strict: true` mode), `python-frontmatter` v1.1.0 for reading and writing YAML frontmatter in `.md` files, and `Typer` v0.12+ for the CLI interface. Contradiction and gap detection require no additional library — pure Python orchestration with Groq API calls. The stack is minimal and aligned with Manuel's existing Python 3.12 + Pydantic v2 preferences.

**Core technologies:**
- `instructor` v1.14.5: structured extraction from raw notes — official Groq integration via `json_schema` strict mode
- `pydantic` v2.x: `KnowledgeEntry` schema definition — already in stack
- `python-frontmatter` v1.1.0: YAML frontmatter read/write for `.md` KB entries — purpose-built, stable
- `Typer` v0.12+: CLI for `ingest`, `process`, `lint` commands — zero boilerplate
- `ChromaDB` v0.5+: semantic search — Phase 4 only, when corpus exceeds ~100 entries
- `sentence-transformers` v3.x: local embeddings — Phase 4, verify CPU inference time first

### Expected Features

**Must have (table stakes):**
- Atomic entry schema — concept, domain, confidence, sources, contradicts, gaps, one-line summary per entry
- Ingest pipeline (`notes/*.md` → `kb/*.md`) — the KB is empty without this
- Contradiction flag on ingest — core differentiator; harder to retrofit than to build now
- Personal context as first-class KB entries — same schema as domain knowledge, domain: `personal_context`
- Claude Code queryability via `CLAUDE.md` — the oracle interface in MVP
- Source attribution on every entry — required for verifiability and confidence tracking
- Reproducibility / idempotency — processing the same note twice must not create duplicates

**Should have (differentiators):**
- Gap detection — system knows what it doesn't know (entry count per domain)
- Confidence propagation in answers — answer confidence reflects source confidence
- Domain coverage map — audit which domains are thin vs. well-covered
- Processing log — which entries created/updated/contradicted per run

**Defer (v2+):**
- KB auto-improvement loop (structured feedback from query corrections)
- `superseded_by` logic — design the field now, implement logic later
- Source quality differentiation — include `source_type` in schema, ignore in queries for MVP
- Semantic search / ChromaDB — add only when corpus exceeds ~100 entries
- Web UI — add only if Claude Code interface proves insufficient

### Architecture Approach

The system is a four-component pipeline. `transcribe.py` (Component 1, existing) produces `notes/*.md`. `process.py` (Component 2, to build) consumes those notes and writes `kb/*.md` (Component 3, to build). Claude Code reads the KB via a `CLAUDE.md` contract (Component 4, to build). Each component has a clean input/output contract. The `notes/` directory is the handoff boundary between what exists and what needs to be built — nothing in the existing pipeline changes.

**Major components:**
1. `transcribe.py` (EXISTS) — URL → `notes/{slug}.md`; treat as black box
2. `process.py` (TO BUILD) — `notes/*.md` → atomic `kb/*.md`; instructor + Groq extraction; merge/contradiction detection; processing log; idempotent
3. `kb/` directory (TO BUILD) — canonical store: `kb/concepts/*.md` + `kb/personal/*.md` + `kb/INDEX.md`
4. `CLAUDE.md` oracle contract (TO BUILD) — instructs Claude Code on KB structure, domain filtering, contradiction surfacing, gap detection protocol

### Critical Pitfalls

1. **Hallucination embedding as permanent fact** — every entry defaults to `confianza: baja`; no automatic promotion; oracle cites source dates; `notes/*.md` source layer preserved
2. **Schema over-engineering before any content exists** — lock at 6 required fields before writing a single entry; every additional field requires a concrete query use case
3. **Collection trap — volume degrades oracle quality** — review gate before committing entries; ~50-entry audit checkpoint to merge, promote, prune
4. **Contradiction model becoming a blocker** — `contradice: [entry_id]` optional field only; no automated graph; flag and surface, never auto-resolve
5. **Schema drift over time** — canonical `schema.md` document; migration script when schema changes; optional fields as `null` on existing entries, not absent

## Implications for Roadmap

### Phase 1: KB Schema + Personal Context Seed
**Rationale:** Every downstream component depends on the schema. Writing `process.py` before schema is locked guarantees a rewrite. Personal context must exist in the KB before any query is meaningful.
**Delivers:** Finalized `schema.md`, `kb/personal/*.md` entries manually authored (escoliosis, pies planos, relevant context), `kb/INDEX.md` template
**Addresses:** Atomic entry schema, personal context as first-class knowledge, source attribution design
**Avoids:** Schema drift (lock before LLM writes entries), schema over-engineering (6 required fields max)

### Phase 2: Knowledge Processor (process.py)
**Rationale:** The KB is empty without this. Building after schema is locked means no mid-implementation schema changes.
**Delivers:** `process.py` CLI with `ingest` and `lint` commands; processes existing 14+ notes into initial `kb/concepts/*.md` corpus; emits processing log; idempotent
**Uses:** `instructor` + Groq, `python-frontmatter`, `Typer`, `pydantic` v2 `KnowledgeEntry` model
**Avoids:** Collection trap (review gate before commit), hallucination embedding (confianza: baja default), premature vector store

### Phase 3: Oracle Interface (CLAUDE.md)
**Rationale:** Requires meaningful KB content to validate. The interface is configuration, not code — but must be designed against real entries to get the query protocol right.
**Delivers:** `CLAUDE.md` at repo root; validated against real queries; domain filtering, contradiction surfacing, gap detection protocol in place
**Avoids:** Query friction abandonment (zero per-session setup), domain bleed (domain as primary filter), context rot (oracle shows entry dates on personal context answers)

### Phase 4: Semantic Search — when corpus > 100 entries
**Rationale:** Plain file reads are sufficient until this threshold. Adding ChromaDB earlier adds sync overhead with zero retrieval benefit.
**Delivers:** Vector index alongside existing `.md` canonical layer; semantic retrieval replaces full KB read
**Uses:** `ChromaDB` v0.5+, `sentence-transformers` v3.x (or Groq embeddings API if available)
**Note:** Verify Groq embedding endpoint availability before planning this phase

### Phase Ordering Rationale

- Schema first because every other component writes or reads it
- Personal context seed in Phase 1 (manually authored, no processor needed) so Phase 3 validation is meaningful from day one
- Processor before oracle because the oracle needs real content to validate query quality against
- ChromaDB deferred: KB starts at 14 notes; 100+ concepts needed before retrieval quality outweighs infra overhead
- No web UI phase planned — add only if Claude Code friction becomes a demonstrated problem

### Research Flags

Phases needing deeper research during planning:
- **Phase 2 (process.py):** Prompt engineering for `KnowledgeEntry` extraction is a design problem, not a library problem. Granularity heuristic (entries per note), merge logic, and contradiction detection prompt all require iteration. Budget for prompt refinement cycles.
- **Phase 4 (ChromaDB):** Verify Groq embedding API availability before designing. If available, eliminates `sentence-transformers`. Re-evaluate LanceDB vs ChromaDB if corpus grows multimodal.

Phases with standard patterns (skip research):
- **Phase 1 (schema):** Pure design decision — schema fields fully specified in ARCHITECTURE.md.
- **Phase 3 (CLAUDE.md):** Well-documented pattern. Direct application of Karpathy LLM Wiki. Build and iterate.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | `instructor` + Groq integration confirmed via official docs. All other tools are stable and widely adopted. |
| Features | HIGH | Feature set derived from Karpathy LLM Wiki (direct) + Zettelkasten atomicity (canonical). MVP scope is clear. |
| Architecture | HIGH | Four-component pipeline maps directly to Karpathy pattern. Component boundaries are clean. Build order is dependency-driven. |
| Pitfalls | HIGH | Karpathy gist (high confidence) + multiple consistent secondary sources on RAG/PKM failure modes. |

**Overall confidence:** HIGH

### Gaps to Address

- **Groq embedding endpoint:** Does Groq expose a text embeddings API? Affects Phase 4 dependency choices. Verify at Phase 4 planning — not blocking earlier phases.
- **Entry granularity heuristic:** How many KB entries per 15-minute video? Define during Phase 2 design. Starting estimate: 3-8 entries per note.
- **Contradiction detection prompt quality:** LLM comparison quality depends on entry serialization format for comparison. Iterative prompt engineering problem — allocate time in Phase 2.
- **INDEX.md format for Claude navigation:** Design specifically for Claude at Phase 1: entry slug + domain + one-sentence summary + file path. Non-negotiable for corpus > 50 entries.

## Sources

### Primary (HIGH confidence)
- Karpathy LLM Wiki gist: https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f
- instructor + Groq integration: https://python.useinstructor.com/integrations/groq/
- python-frontmatter: https://pypi.org/project/python-frontmatter/
- Zettelkasten atomicity: https://zettelkasten.de/atomicity/guide/

### Secondary (MEDIUM confidence)
- Karpathy LLM Wiki pattern breakdown: https://www.mindstudio.ai/blog/andrej-karpathy-llm-wiki-knowledge-base-claude-code
- RAG best practices: https://www.kapa.ai/blog/rag-best-practices
- PKM failure analysis: https://medium.com/@ann_p/your-second-brain-is-broken-why-most-pkm-tools-waste-your-time-76e41dfc6747
- Building Lattice (frontmatter + YAML for Claude Code KB): https://uptownhr.com/blog/building-lattice-knowledge-graph-cli/
- RAG contradiction detection: https://arxiv.org/html/2504.00180v1
- Staleness and outdated KB entries: https://shelf.io/blog/outdated-knowledge-base/

---
*Research completed: 2026-04-08*
*Ready for roadmap: yes*
