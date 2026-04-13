# Phase 4: Semantic Search - Research

**Researched:** 2026-04-13
**Domain:** Vector databases, local embeddings, ChromaDB, Python integration
**Confidence:** HIGH

## Summary

Phase 4 adds a ChromaDB vector index as an additive layer over the existing `kb/*.md` corpus. The canonical YAML frontmatter files are the source of truth — ChromaDB is a read-acceleration cache populated from them, not a replacement. The current corpus stands at 205 concept entries + 4 personal entries, marginally above the ~100-entry threshold the roadmap set as the trigger.

The integration is local-only: `chromadb.PersistentClient` writes a SQLite + HNSW index to a directory on disk. Embeddings run locally via `sentence-transformers` — no API key, no external service. The slug (`concept` frontmatter field) is the natural document ID, enabling idempotent `upsert` calls on every `ingest` run. Query path replaces the INDEX.md full-domain-read with a semantic `collection.query()` call filtered by `domain` metadata, returning only the N most relevant entries instead of all entries in a domain.

**Primary recommendation:** Use `chromadb` with `SentenceTransformerEmbeddingFunction(model_name="paraphrase-multilingual-MiniLM-L12-v2")` — the KB contains mixed Spanish/English content and the default `all-MiniLM-L6-v2` is English-only.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| chromadb | 1.5.7 (2026-04-08) | Vector store + HNSW index | Official package, persistent local mode, built-in embedding support |
| sentence-transformers | latest via chromadb dep | Local embedding generation | No API key, runs on CPU, 50+ language support |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| python-frontmatter | 1.1.0 (already installed) | Parse KB entry metadata | Loading slugs, domain, summary, body for upsert |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| local sentence-transformers | OpenAI/Groq embeddings | Would add API dependency and cost; local is sufficient for 200-entry corpus |
| paraphrase-multilingual-MiniLM-L12-v2 | all-MiniLM-L6-v2 (ChromaDB default) | Default is English-only; KB has Spanish content in summaries and bodies |
| chromadb PersistentClient | Qdrant, pgvector, FAISS | ChromaDB is simplest for local single-user, no server required |

**Installation:**
```bash
pip install chromadb sentence-transformers
```

**Version verification:** chromadb 1.5.7 confirmed via PyPI (2026-04-08). sentence-transformers installs as a chromadb dependency when `SentenceTransformerEmbeddingFunction` is used.

## Architecture Patterns

### Recommended Project Structure
```
kb/
├── concepts/        # Source of truth — unchanged
├── personal/        # Source of truth — unchanged
└── INDEX.md         # Source of truth — unchanged

.chroma/             # Vector index (gitignored, derived artifact)
  └── chroma.sqlite3 + UUID dirs

process.py           # Add: rebuild_vector_index(), query_vector_index()
```

The `.chroma/` directory is a derived artifact — it can be deleted and rebuilt from `kb/` at any time. It should be in `.gitignore`.

### Pattern 1: Slug-as-ID Upsert

**What:** Use the KB entry's `concept` slug as the ChromaDB document ID. Call `upsert()` on every ingest run.
**When to use:** Every time a new entry is written to `kb/concepts/`. Idempotent — re-ingesting the same slug overwrites its vector without creating duplicates.
**Example:**
```python
# Source: https://docs.trychroma.com/guides
import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

CHROMA_PATH = ".chroma"
COLLECTION_NAME = "secondbrain"

def _get_collection():
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    ef = SentenceTransformerEmbeddingFunction(
        model_name="paraphrase-multilingual-MiniLM-L12-v2"
    )
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=ef,
    )

def upsert_entry(slug: str, document_text: str, domain: str, confidence: float) -> None:
    col = _get_collection()
    col.upsert(
        ids=[slug],
        documents=[document_text],
        metadatas=[{"domain": domain, "confidence": confidence}],
    )
```

### Pattern 2: Domain-Filtered Semantic Query

**What:** Query the collection with a natural-language string, filtered to one or more domains.
**When to use:** At query time in the oracle protocol, replacing the INDEX.md full-domain-read when corpus is large.
**Example:**
```python
# Source: https://docs.trychroma.com/docs/querying-collections/metadata-filtering
def query_vector_index(query: str, domains: list[str], n_results: int = 10) -> list[str]:
    col = _get_collection()
    where = {"domain": {"$in": domains}} if len(domains) > 1 else {"domain": domains[0]}
    results = col.query(
        query_texts=[query],
        n_results=n_results,
        where=where,
    )
    # Returns slugs of top N semantically relevant entries
    return results["ids"][0]
```

### Pattern 3: Full Rebuild Subcommand

**What:** Scan all `kb/concepts/*.md` and `kb/personal/*.md`, delete existing collection, recreate from scratch.
**When to use:** After bulk ingests, or when the embedding model changes (embedding space is not portable across models).
**Example:**
```python
def rebuild_vector_index(
    concepts_dir: Path = KB_CONCEPTS_DIR,
    personal_dir: Path = KB_PERSONAL_DIR,
) -> int:
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    # Delete and recreate to avoid stale entries
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass
    ef = SentenceTransformerEmbeddingFunction(
        model_name="paraphrase-multilingual-MiniLM-L12-v2"
    )
    col = client.create_collection(name=COLLECTION_NAME, embedding_function=ef)

    ids, docs, metas = [], [], []
    for md_path in sorted(concepts_dir.glob("*.md")) + sorted(personal_dir.glob("*.md")):
        post = frontmatter.load(str(md_path))
        slug = post.metadata.get("concept", md_path.stem)
        domain = post.metadata.get("domain", "")
        summary = post.metadata.get("summary", "")
        body = post.content or ""
        document_text = f"{summary}\n{body}".strip()
        ids.append(slug)
        docs.append(document_text)
        metas.append({"domain": domain, "confidence": float(post.metadata.get("confidence", 0))})

    if ids:
        col.upsert(ids=ids, documents=docs, metadatas=metas)
    return len(ids)
```

### Pattern 4: Incremental Sync on Ingest

**What:** After `write_kb_entry()` succeeds in the existing `ingest_note()` flow, immediately upsert that single entry into the vector index.
**When to use:** Normal ingest — keeps vector index in sync without a full rebuild.

This is the same as Pattern 1, called at the end of the per-concept write loop inside `ingest_note()`, mirroring the existing `rebuild_index()` call pattern.

### Anti-Patterns to Avoid
- **Changing the embedding model mid-collection:** The vector space is model-specific. If the model changes, the entire collection must be rebuilt. Pin the model name as a constant.
- **Storing only summaries:** The summary alone is a single sentence — too sparse. Concatenate `summary + body` as the document text for richer semantic coverage.
- **Making vector index the source of truth:** The `kb/*.md` files are the source of truth. If ChromaDB is deleted, `rebuild-vector-index` must recreate it fully. The vector index is never written to outside of ChromaDB.
- **Replacing the oracle's full-read protocol:** The vector index should narrow the read set (e.g., top 10 results), not replace schema parsing, contradiction checking, or gap detection — those still happen on the retrieved `kb/*.md` files.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Vector similarity search | Custom cosine similarity loop | `collection.query()` | HNSW index is correct, fast, handles >10k entries; manual cosine is O(n) |
| Embedding generation | Own tokenization/model loading | `SentenceTransformerEmbeddingFunction` | Thread safety, model caching, batching handled internally |
| Persistent storage | Custom SQLite + pickle | `chromadb.PersistentClient` | WAL, crash recovery, atomic writes built in |
| Metadata filtering | Post-filter query results | `where` parameter in `collection.query()` | Pre-filtered at index level, avoids loading all results |

**Key insight:** ChromaDB is the complete stack for this use case. The only custom code is the bridge between KB frontmatter and the ChromaDB API.

## Common Pitfalls

### Pitfall 1: English-only default embedding model
**What goes wrong:** ChromaDB's default model (`all-MiniLM-L6-v2`) produces poor embeddings for Spanish text. Queries in Spanish return irrelevant results.
**Why it happens:** Default model trained on English data only. KB entries have Spanish summaries (written by LLM with Spanish context) and Spanish bodies.
**How to avoid:** Explicitly set `model_name="paraphrase-multilingual-MiniLM-L12-v2"` in `SentenceTransformerEmbeddingFunction`. Never rely on the default.
**Warning signs:** Semantic queries for Spanish terms return irrelevant English-domain entries.

### Pitfall 2: Collection/model mismatch after model change
**What goes wrong:** Existing collection was built with model A, new code uses model B. Vectors are incompatible — queries return garbage.
**Why it happens:** Embeddings are model-specific; there is no automatic migration.
**How to avoid:** Pin model name as a constant (`VECTOR_EMBEDDING_MODEL`). If model must change, run `rebuild-vector-index` to recreate the collection from scratch.
**Warning signs:** Query results are obviously wrong after any config change.

### Pitfall 3: n_results > collection size crash
**What goes wrong:** `collection.query(n_results=10)` raises an error when fewer than 10 documents exist.
**Why it happens:** ChromaDB enforces `n_results <= collection.count()`.
**How to avoid:** Clamp: `n_results = min(n_results, collection.count())`.
**Warning signs:** Tests with small isolated fixtures crash on query.

### Pitfall 4: First model download blocks tests
**What goes wrong:** First run downloads ~120MB model from HuggingFace Hub. In CI or test environments without network, this fails silently or times out.
**Why it happens:** `SentenceTransformerEmbeddingFunction` downloads on first use.
**How to avoid:** Mark vector index tests as `integration` (already the project pattern). Unit tests should not instantiate the embedding function. In integration tests, accept the download or pre-cache the model.
**Warning signs:** Test timeouts on first run in clean environment.

### Pitfall 5: `.chroma/` committed to git
**What goes wrong:** Binary index files (~tens of MB) pollute git history. Rebuild is fast — storing the index in git is wasteful.
**Why it happens:** Forgetting to gitignore a new directory.
**How to avoid:** Add `.chroma/` to `.gitignore` before first `PersistentClient` run.
**Warning signs:** `git status` shows `.chroma/` as untracked.

## Code Examples

### Full sync integration with ingest_note()
```python
# Source: pattern derived from existing process.py structure
# Called at the end of write_kb_entry() success branch in ingest_note()

def _sync_to_vector_index(concept: dict, kb_dir: Path) -> None:
    """Non-critical: log warning on failure, never raise."""
    try:
        slug = concept["concept"]
        summary = concept.get("summary", "")
        body = concept.get("body", "")
        domain = concept.get("domain", "")
        confidence = float(concept.get("confidence", 0))
        document_text = f"{summary}\n{body}".strip()
        upsert_entry(slug, document_text, domain, confidence)
    except Exception as e:
        print(f"[WARN] vector index sync failed for {concept.get('concept')}: {e}")
```

### rebuild-vector-index CLI subcommand signature
```python
# Added to process.py alongside existing rebuild-index subcommand
p_rebuild_vec = sub.add_parser(
    "rebuild-vector-index",
    help="Rebuild ChromaDB vector index from all kb/ entries"
)
p_rebuild_vec.add_argument(
    "--chroma-path", default=".chroma",
    help="Path to ChromaDB persistent storage directory"
)
p_rebuild_vec.set_defaults(func=_cmd_rebuild_vector_index)
```

### Query returning entry slugs for oracle use
```python
# Source: https://docs.trychroma.com/docs/querying-collections/metadata-filtering
def query_vector_index(
    query: str,
    domains: list[str],
    n_results: int = 10,
    chroma_path: str = ".chroma",
) -> list[str]:
    client = chromadb.PersistentClient(path=chroma_path)
    ef = SentenceTransformerEmbeddingFunction(
        model_name=VECTOR_EMBEDDING_MODEL
    )
    col = client.get_or_create_collection(COLLECTION_NAME, embedding_function=ef)
    count = col.count()
    if count == 0:
        return []
    clamped = min(n_results, count)
    if len(domains) == 1:
        where = {"domain": domains[0]}
    else:
        where = {"domain": {"$in": domains}}
    results = col.query(
        query_texts=[query],
        n_results=clamped,
        where=where,
    )
    return results["ids"][0]  # list of slugs
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `chromadb.Client()` (in-memory) | `chromadb.PersistentClient(path=...)` | v0.4+ | Data survives process exit |
| Manual embedding + FAISS | Built-in SentenceTransformerEmbeddingFunction | v0.3+ | No embedding boilerplate |
| `collection.add()` with dedup logic | `collection.upsert()` | v0.3+ | Idempotent ingest, no manual check |
| `EphemeralClient` / `Client()` | `chromadb.EphemeralClient()` | v0.5+ | Renamed but same behavior for tests |

**Deprecated/outdated:**
- `chromadb.Client()`: Replaced by `chromadb.EphemeralClient()` for in-memory and `chromadb.PersistentClient()` for persistent. Old alias may still work but avoid in new code.

## Open Questions

1. **CLAUDE.md oracle protocol update scope**
   - What we know: Current CLAUDE.md query protocol reads all entries in a domain from INDEX.md. With semantic search, it should instead call the vector index and read only returned slugs.
   - What's unclear: Whether Phase 4 should update CLAUDE.md to replace the protocol, or define a parallel path.
   - Recommendation: Keep the full-read path as fallback; vector index path is invoked when corpus per domain exceeds a threshold (e.g., >20 entries). Update CLAUDE.md as part of the phase.

2. **Corpus language distribution**
   - What we know: KB entries are authored in English (slugs, some bodies) with Spanish summaries in some entries.
   - What's unclear: Exact ratio of Spanish vs English content across 205 entries.
   - Recommendation: `paraphrase-multilingual-MiniLM-L12-v2` handles both correctly; this is not a blocker.

3. **personal/ entries in the vector index**
   - What we know: 4 personal entries exist. The oracle always loads all of them unconditionally (session initialization).
   - What's unclear: Whether personal entries should be in the same collection or excluded.
   - Recommendation: Include personal/ in the collection — they can be retrieved semantically when relevant. The oracle's mandatory full-load of personal/ at session start is separate from domain queries.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (existing, pytest.ini present) |
| Config file | `pytest.ini` — testpaths = tests |
| Quick run command | `pytest tests/ -m "not integration" -x` |
| Full suite command | `pytest tests/ -x` |

### Phase Requirements → Test Map

Phase 4 has no formal requirement IDs (v2 scope). Success criteria map to tests as follows:

| Success Criterion | Behavior | Test Type | Automated Command | File Exists? |
|-------------------|----------|-----------|-------------------|-------------|
| SC-1: ChromaDB populated from kb/*.md | `rebuild-vector-index` populates collection with correct count | unit | `pytest tests/test_vector_index.py::test_rebuild_populates_collection -x` | ❌ Wave 0 |
| SC-1: Stays in sync on ingest | After `ingest_note()`, slug appears in collection | unit | `pytest tests/test_vector_index.py::test_ingest_syncs_vector_index -x` | ❌ Wave 0 |
| SC-2: Semantic query beats keyword | Query returns relevant entry in top-3 on real corpus | integration | `pytest tests/test_vector_index.py -m integration -x` | ❌ Wave 0 |
| SC-3: kb/*.md unchanged | After rebuild, no frontmatter file is modified | unit | `pytest tests/test_vector_index.py::test_kb_files_untouched -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/ -m "not integration" -x`
- **Per wave merge:** `pytest tests/ -x` (integration tests require no Groq API, only local model download)
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_vector_index.py` — unit + integration tests for vector index
- [ ] `.gitignore` entry for `.chroma/`
- [ ] `pip install chromadb sentence-transformers` — neither installed currently

## Sources

### Primary (HIGH confidence)
- [ChromaDB PyPI](https://pypi.org/project/chromadb/) — version 1.5.7 confirmed, 2026-04-08
- [ChromaDB Getting Started](https://docs.trychroma.com/docs/overview/getting-started) — PersistentClient, upsert, query API
- [ChromaDB Embedding Functions](https://docs.trychroma.com/docs/embeddings/embedding-functions) — SentenceTransformerEmbeddingFunction, default model
- [ChromaDB Metadata Filtering](https://docs.trychroma.com/docs/querying-collections/metadata-filtering) — where filter syntax
- [Chroma Cookbook - Collections](https://cookbook.chromadb.dev/core/collections/) — get_or_create_collection, upsert vs add, delete patterns

### Secondary (MEDIUM confidence)
- [HuggingFace: paraphrase-multilingual-MiniLM-L12-v2](https://huggingface.co/sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2) — 50+ language support, 384-dim vectors
- [ChromaDB GitHub - SentenceTransformerEmbeddingFunction](https://github.com/chroma-core/chroma/blob/main/chromadb/utils/embedding_functions/sentence_transformer_embedding_function.py) — implementation reference
- [Chroma Cookbook - Rebuilding](https://cookbook.chromadb.dev/strategies/rebuilding/) — full rebuild vs incremental patterns

### Tertiary (LOW confidence)
- WebSearch results on sync patterns with markdown files — no single authoritative source; patterns derived from official API docs

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — versions verified via PyPI, API confirmed via official docs
- Architecture: HIGH — patterns follow directly from official ChromaDB API + existing process.py structure
- Pitfalls: MEDIUM — multilingual pitfall confirmed via HuggingFace docs; others derived from API semantics

**Research date:** 2026-04-13
**Valid until:** 2026-07-13 (ChromaDB moves fast — re-verify API if planning after this date)
