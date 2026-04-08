# Stack Research: Second Brain — El Oráculo

**Researched:** 2026-04-08
**Mode:** Ecosystem (existing pipeline, .md canonical layer, Claude as interface)

---

## Recommended Stack

### Structured Output from LLM (note → atomic KB entry)

- **instructor** v1.14.5 — First-class Groq integration via `instructor.from_provider()`. Schema-first, Pydantic-native, no agent overhead. Simpler than PydanticAI for extraction-only tasks. Groq supports `json_schema` with `strict: true` constrained decoding. This is the exact pattern needed: take a `notes/*.md`, define a Pydantic `KnowledgeEntry` model, call Groq, get back validated structured output. No extra machinery.
  - Confidence: HIGH (official Groq docs + instructor docs both confirm integration)
  - Source: https://python.useinstructor.com/integrations/groq/

- **pydantic** v2.x — Schema definition for `KnowledgeEntry` (concept, domain, confidence, sources, contradicts, extends, gaps). Already aligned with Manuel's stack. Use `model.model_dump()` to serialize to YAML frontmatter.
  - Confidence: HIGH

### Frontmatter Read/Write (.md canonical layer)

- **python-frontmatter** v1.1.0 (package: `python-frontmatter`) — Reads and writes YAML frontmatter in .md files. Clean API: `frontmatter.load(path)` returns post with `.metadata` dict and `.content` string. `frontmatter.dump(post)` round-trips cleanly. The correct package — not the `frontmatter` package (v3.0.8, different maintainer, less used in this context).
  - Confidence: HIGH (official docs at python-frontmatter.readthedocs.io)
  - Source: https://pypi.org/project/python-frontmatter/

- **PyYAML** v6.x — Already a transitive dependency of python-frontmatter. Use directly when generating frontmatter blocks programmatically (e.g., writing new KB entries from scratch).
  - Confidence: HIGH

### CLI Interface (ingest commands, KB maintenance)

- **Typer** v0.12+ — Type-hint-driven CLI, zero boilerplate, built on Click. Commands like `python kb.py ingest note.md`, `python kb.py lint`, `python kb.py query "pregunta"` are straightforward to implement. Consistent with Python 3.12 type hint style. No need for argparse verbosity or Click decorator overhead.
  - Confidence: HIGH (widely adopted, well-maintained)
  - Source: https://typer.tiangolo.com/

### Contradiction & Gap Detection (KB maintenance)

No dedicated library needed. The pattern (validated by Karpathy's llm-wiki architecture and knowledgebase_guardian project) is:

1. Load all KB entries via python-frontmatter
2. For each new entry, embed the `contradicts` field check as part of instructor extraction prompt: "Does this contradict any of: [existing entries on same domain]?"
3. Periodically run a `lint` command that passes all entries in a domain to the LLM and asks it to flag contradictions, stale claims, and gaps

This is pure Python + Groq API — no extra library. The LLM does the reasoning; the Python script orchestrates file I/O.
  - Confidence: MEDIUM (pattern verified in multiple community implementations, not a single canonical library)

### File Watching (optional automation, not MVP)

- **watchdog** v4.x — Cross-platform filesystem events. Triggers `ingest` when a new file lands in `notes/`. Explicitly out of scope for MVP (PROJECT.md: "ingesta automática — demasiado complejo para MVP") but the standard choice when needed.
  - Confidence: HIGH

### Vector Store (Phase 2 only, corpus > ~100 concepts)

- **ChromaDB** v0.5+ — Recommended over LanceDB for this use case. Reasons: simpler Python API, persistent local storage (SQLite+files, no server), faster to prototype. LanceDB is faster at scale (Rust-based, columnar) but that advantage is irrelevant at < 1000 entries. ChromaDB's in-process mode (`chromadb.PersistentClient(path="./chroma_db")`) is zero-ops.
  - Confidence: HIGH for small corpus fit; MEDIUM for long-term (LanceDB may be better if corpus grows multimodal)
  - Source: https://www.altexsoft.com/blog/chroma-pros-and-cons/

- **sentence-transformers** v3.x — Local embeddings via `all-MiniLM-L6-v2` model (384 dims, 80MB). No API cost for embeddings. Runs on CPU for a personal KB. Alternative: use Groq's embeddings API if available, but local is more stable for offline use.
  - Confidence: MEDIUM (standard choice, but verify Groq embedding endpoint availability before Phase 2)

### Existing Pipeline (do not change)

The pipeline already works for 14/14 posts. No changes to:
- `yt-dlp` — video/audio download
- `groq` Python SDK — Whisper (transcription) + Llama 4 Vision (image/carousel extraction)

The new processing layer (notes → KB entries) sits downstream of these, reading `notes/*.md` as input.

---

## Architecture Pattern: Karpathy llm-wiki

The validated pattern for this exact use case (published April 2026, directly applicable):

```
notes/*.md  (pipeline output — immutable raw layer)
    ↓
processor.py (instructor + Groq + python-frontmatter)
    ↓
kb/*.md  (atomic KB entries — canonical layer, LLM-maintained)
    ↓
Claude Code  (reads kb/*.md, reasons over them, answers queries)
```

The KB index file (`kb/INDEX.md`) lists all entries with their domains and concept names, enabling Claude to find relevant entries without reading every file. This is the "grep-compatible" pattern — simple file operations, no infrastructure.

---

## What NOT to Use

| Tool | Why Not |
|------|---------|
| **LangChain** | Massive abstraction overhead for a pipeline that's already working. Adds 500+ transitive dependencies for zero benefit here. The pipeline is Python scripts + Groq SDK directly — keep it that way. |
| **LlamaIndex** | Same problem as LangChain. Useful for complex RAG orchestration, overkill for structured extraction from local .md files. |
| **PydanticAI** | Launched late 2025, ecosystem still maturing. Adds agent/observability abstractions not needed for simple extraction. Instructor does the same job in fewer lines. |
| **Obsidian** | Good as a viewer but do not make it the canonical layer — it adds proprietary linking syntax and plugin lock-in. Keep canonical layer as plain .md with YAML frontmatter. |
| **SQLite for KB** | Tempting but wrong for MVP. .md files are readable by Claude directly, versionable with git, editable by hand. SQLite requires a query layer between Claude and the data. |
| **LanceDB (Phase 2)** | Technically superior at scale, but ChromaDB's simpler API wins for a corpus that will stay under 10K entries. Revisit if multimodal embeddings become needed. |
| **OpenAI API** | Pipeline already uses Groq — switching providers adds cost and complexity for no benefit given Llama 4's capability for knowledge extraction tasks. |

---

## Confidence Levels

| Component | Confidence | Notes |
|-----------|------------|-------|
| instructor + Groq | HIGH | Official integration, cookbook examples, `strict: true` JSON schema |
| pydantic v2 schema | HIGH | Core dependency, already in Manuel's stack |
| python-frontmatter | HIGH | Stable, purpose-built, no alternatives worth considering |
| Typer CLI | HIGH | Widely adopted, zero controversy |
| Contradiction detection via LLM | MEDIUM | Pattern validated by community but no canonical library; prompt engineering quality matters |
| ChromaDB for Phase 2 | HIGH (fit) / MEDIUM (longevity) | Good for <10K entries; LanceDB should be re-evaluated at Phase 2 planning |
| sentence-transformers local | MEDIUM | Standard choice but verify hardware (CPU inference time acceptable for personal use) |

---

## Open Questions

1. **Groq embedding endpoint**: Does Groq expose an embeddings API? If yes, it eliminates sentence-transformers as a dependency for Phase 2. Verify at Phase 2 planning.

2. **KB entry granularity**: How atomic is "atomic"? A single concept from a 15-minute video may yield 3-8 entries. Define the splitting heuristic in the `KnowledgeEntry` Pydantic model design phase.

3. **Contradiction detection prompt quality**: LLM-based contradiction detection quality depends heavily on how entries are serialized before comparison. This is a design decision, not a library choice — needs iteration.

4. **Claude Code KB reading strategy**: For >50 entries, Claude reading all files individually is slow. An `INDEX.md` with one-line summaries per entry is essential from the start — design KB schema to support it.
