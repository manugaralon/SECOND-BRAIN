# Architecture Patterns

**Domain:** Personal adaptive knowledge oracle (RAG-adjacent, PKM-adjacent)
**Researched:** 2026-04-08

## Recommended Architecture

```
[Raw Source URLs]
       |
       v
[Ingestion Pipeline]  ← transcribe.py (EXISTS)
  yt-dlp + Whisper
  Llama 4 Vision
       |
       v
[notes/*.md]          ← intermediate output, NOT the KB
  raw transcripts
  with frontmatter
       |
       v
[Knowledge Processor] ← TO BUILD (Component 2)
  reads notes/*.md
  extracts atomic concepts
  resolves contradictions
  detects gaps
       |
       v
[KB Store: kb/*.md]   ← TO BUILD (Component 3)
  one file per concept
  YAML frontmatter schema
  canonical layer
       |
       v
[Query Interface]     ← TO BUILD (Component 4)
  Claude Code reads KB
  reasons holistically
  synthesizes response
```

### Component Boundaries

| Component | Responsibility | Input | Output | Communicates With |
|-----------|---------------|-------|--------|-------------------|
| Ingestion Pipeline (`transcribe.py`) | URL → structured raw note | URL | `notes/*.md` | External APIs (Groq, yt-dlp) |
| Knowledge Processor (`process.py`) | Raw note → atomic KB entries | `notes/*.md` | `kb/*.md` | Groq/LLM API, KB Store |
| KB Store (`kb/`) | Canonical knowledge, versioned | writes from Processor | `.md` files with frontmatter | Processor (write), Query (read) |
| Query Interface (Claude Code + CLAUDE.md) | Holistic reasoning over KB | User question + KB read | Synthesized answer | KB Store (read) |

### Directory Layout

```
SECONDBRAIN/
├── transcribe.py          # EXISTS — ingestion pipeline
├── notes/                 # EXISTS — raw intermediate notes
│   └── *.md               # one per URL, with frontmatter
├── process.py             # TO BUILD — knowledge processor
├── kb/                    # TO BUILD — canonical KB
│   ├── concepts/          # domain knowledge entries
│   │   └── *.md
│   └── personal/          # Manuel's context (treated identically)
│       └── *.md
└── CLAUDE.md              # TO BUILD — oracle instructions for Claude Code
```

## Data Flow

### Ingestion Path (existing)

```
URL
 → yt-dlp download (video) / direct fetch (image/carousel)
 → Whisper transcription (video) / Llama 4 Vision description (image)
 → LLM structuring pass
 → notes/{slug}.md with frontmatter (title, source_url, date, domain, raw_content)
```

### Processing Path (to build)

```
notes/{slug}.md
 → LLM extraction pass: identify atomic concepts in this note
 → For each concept:
     - Does kb/concepts/{concept}.md exist?
       YES → merge/extend/flag contradiction if present
       NO  → create new entry with schema
 → Write/update kb/*.md
 → Emit processing log (which entries created/updated/contradicted)
```

### Query Path (to build)

```
User question (in Claude Code)
 → Claude reads CLAUDE.md (oracle instructions: "you have access to kb/, read relevant files")
 → Claude reads relevant kb/*.md files (full text, not embeddings — corpus is small)
 → Claude reasons holistically, applying personal context from kb/personal/
 → Synthesized response with concept attribution
```

## KB Entry Schema (frontmatter)

```yaml
---
concept: "name of the atomic concept"
domain: "fisioterapia | IA | finanzas | trading | psicología | esoterismo | deportes | personal"
confidence: 0.0-1.0      # weighted by source quality and agreement
sources:
  - url: "https://..."
    note: "notes/slug.md"
    date: "2026-04-08"
contradicts:
  - concept: "other-concept"
    detail: "brief description of the contradiction"
extends:
  - concept: "parent-concept"
gaps:
  - "what is not yet known about this concept"
last_updated: "2026-04-08"
---

[Body: plain text synthesis of the concept, personalized to Manuel's context where relevant]
```

## Patterns to Follow

### Pattern 1: Incremental KB Integration

**What:** When processing a new note, the processor checks existing KB entries before writing. New information either creates a new entry or merges with an existing one.

**When:** Every time `process.py` runs on a new note.

**Why:** Prevents concept duplication. Enables contradiction detection. Builds a coherent KB rather than a dump of isolated notes. This is the Karpathy LLM-wiki pattern — LLM incrementally maintains a structured wiki, integrating new sources into existing entries.

**Implementation sketch:**

```python
def process_note(note_path: Path, kb_dir: Path, llm_client):
    note = load_note(note_path)
    existing_concepts = load_kb_index(kb_dir)  # slug → file path
    
    extracted = llm_extract_concepts(note, existing_concepts, llm_client)
    # extracted: list of {concept, domain, content, contradicts?, extends?}
    
    for entry in extracted:
        kb_path = kb_dir / slugify(entry.concept) + ".md"
        if kb_path.exists():
            existing = load_kb_entry(kb_path)
            merged = llm_merge_entries(existing, entry, llm_client)
            write_kb_entry(kb_path, merged)
        else:
            write_kb_entry(kb_path, entry)
```

### Pattern 2: Personal Context as First-Class Knowledge

**What:** Manuel's personal context (escoliosis, pies planos, etc.) is stored in `kb/personal/` using the same schema as domain knowledge, not as a separate profile.

**When:** Onboarding phase — manually authored or extracted from a structured intake.

**Why:** The oracle reasons holistically. Separating personal context forces artificial join logic at query time. With a unified schema, Claude Code reads personal and domain entries identically and synthesizes naturally.

### Pattern 3: CLAUDE.md as Oracle Contract

**What:** A `CLAUDE.md` at the project root instructs Claude Code on how to use the KB. It defines the query protocol: which directories to read, how to attribute sources, how to handle gaps and contradictions in responses.

**When:** Built once in the oracle phase, refined as KB grows.

**Why:** Claude Code's behavior is governed by CLAUDE.md. This is the correct integration point — no new tooling needed for the MVP query interface.

### Pattern 4: Processing Log for Reproducibility

**What:** `process.py` emits a log per run: which notes were processed, which KB entries were created/updated, any contradictions flagged.

**When:** Every processing run.

**Why:** Makes the pipeline auditable. Contradictions that need human review are surfaced explicitly rather than silently merged.

## Anti-Patterns to Avoid

### Anti-Pattern 1: Treating notes/*.md as the KB

**What goes wrong:** Querying directly against raw notes instead of processed KB entries.

**Why bad:** Raw notes are verbose, redundant, and unresolved. Claude's context window fills with noise. Contradictions are not surfaced. Personal context is not integrated.

**Instead:** Always query `kb/`, never `notes/` directly in the oracle context.

### Anti-Pattern 2: One Big Knowledge File

**What goes wrong:** Merging all KB entries into a single `knowledge.md`.

**Why bad:** Claude has to read everything to find anything. Contradictions are hard to detect. Updating one concept risks corrupting others. No granular confidence tracking.

**Instead:** One file per concept, indexed by filename slug. Claude reads selectively.

### Anti-Pattern 3: Adding ChromaDB/Embeddings Before the Corpus Justifies It

**What goes wrong:** Building semantic search infrastructure at <100 concepts.

**Why bad:** Infrastructure complexity for zero marginal benefit — Claude can read 100 markdown files in a single context window. The operational overhead exceeds the retrieval quality gain at this scale.

**Instead:** Plain file reads until corpus exceeds ~100 concepts. ChromaDB is a Phase 2 upgrade, not a Day 1 requirement.

### Anti-Pattern 4: LLM Extraction Without Idempotency

**What goes wrong:** Running the processor on a note that was already processed, creating duplicate KB entries.

**Why bad:** Duplicate concepts, inflated confidence scores, contradictions with itself.

**Instead:** Processor tracks which notes have been processed (e.g., a `processed.log` or a frontmatter flag in the note). Skip already-processed notes unless `--force` flag is passed.

## Build Order (Dependencies)

```
Phase 1: KB Schema + Personal Context
  - Define the frontmatter schema (no code, just spec)
  - Author kb/personal/*.md manually (Manuel's physical context, etc.)
  - No dependencies — can start immediately

Phase 2: Knowledge Processor (process.py)
  - Depends on: notes/*.md existing (pipeline already produces these)
  - Depends on: KB schema finalized (Phase 1)
  - Output: kb/concepts/*.md populated from existing notes corpus

Phase 3: Oracle Interface (CLAUDE.md)
  - Depends on: KB having meaningful content (Phase 2 complete)
  - Output: Claude Code can query and synthesize from kb/
  - Validate: ask test questions, verify synthesis quality

Phase 4 (future): ChromaDB Semantic Search
  - Depends on: corpus > ~100 concepts
  - Replaces: plain file reads with semantic retrieval
  - Does NOT change KB schema — additive upgrade
```

## How the Existing Pipeline Fits In

`transcribe.py` is Component 1. It is complete and stable. The architecture treats it as a black box:

- **Input contract:** URL (video, image, carousel)
- **Output contract:** `notes/{slug}.md` with frontmatter (title, source_url, date, domain, raw_content or transcript)
- **Integration point:** `process.py` reads from `notes/` — that is the only coupling

No changes to `transcribe.py` are required. The processor is purely additive. The `notes/` directory is the handoff boundary between what exists and what is to be built.

## Scalability Considerations

| Concern | Now (<50 concepts) | Phase 2 (~100-500 concepts) | Phase 3 (>500 concepts) |
|---------|-------------------|----------------------------|-------------------------|
| Retrieval | Full KB read in context | Full KB read still viable | Semantic search needed |
| Processing | Single LLM pass per note | Same — stateless per note | Batch processing / async |
| Storage | Flat `kb/concepts/` dir | Flat dir still fine | Subdirectories by domain |
| Contradictions | Flagged in frontmatter | Same | Dedicated contradiction index |
| Query interface | Claude Code + CLAUDE.md | Same | Consider web UI if friction felt |

## Sources

- Karpathy LLM-wiki pattern: incremental wiki maintenance by LLM (MEDIUM confidence — widely referenced pattern, no single canonical doc)
- [From Unstructured Text to Interactive Knowledge Graphs Using LLMs](https://robert-mcdermott.medium.com/from-unstructured-text-to-interactive-knowledge-graphs-using-llms-dd02a1f71cd6) — atomic concept extraction approach
- [Building Lattice: A Knowledge Graph for Claude Code](https://uptownhr.com/blog/building-lattice-knowledge-graph-cli/) — frontmatter + YAML for machine-readable KB in Claude Code context
- [Effective Practices for Architecting a RAG Pipeline](https://www.infoq.com/articles/architecting-rag-pipeline/) — two-phase pipeline (indexing vs retrieval) pattern
- [Building a Smart PKM System with RAG and Knowledge Graphs](https://medium.com/@nima.mz.azari/building-a-smart-personal-knowledge-management-system-with-rag-and-knowledge-graphs-cb9e94b7e42d) — hybrid PKM architecture
- PROJECT.md constraints and key decisions — authoritative for this system's scope
