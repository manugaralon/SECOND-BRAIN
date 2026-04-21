# Second Brain — Personal Knowledge Oracle

A personal knowledge base (KB) powered by Claude Code. Notes are ingested, structured, and semantically indexed. Claude Code acts as an oracle: it queries the KB, cross-applies personal context, and synthesizes personalized answers.

## Architecture

```
pipeline/notes/     ← raw notes (video transcriptions, carousels, etc.)
       │
       ▼ process.py ingest
kb/
  concepts/         ← ~350 atomic domain knowledge entries
  personal/         ← Manuel's personal context (4 entries, always loaded)
  INDEX.md          ← full slug | domain | summary | path index
.chroma/            ← ChromaDB vector index (semantic search)
```

## Domains

`fisioterapia` · `ia` · `finanzas` · `trading` · `esoterismo` · `psicologia` · `deportes` · `personal`

## How It Works

1. **Ingest** — drop a raw note (video transcript, carousel text) into `pipeline/notes/` and run the processor. Groq LLM extracts atomic concepts and writes structured Markdown files with YAML frontmatter into `kb/concepts/`.

2. **Index** — `kb/INDEX.md` is auto-regenerated after each ingest. Each entry maps a slug to a domain, summary, and file path.

3. **Vector search** — ChromaDB + `paraphrase-multilingual-MiniLM-L12-v2` embeddings enable semantic search over the KB. Domains with > 20 entries are queried via vector search; smaller domains are read in full.

4. **Oracle query** — Claude Code reads personal context at session start, determines relevant domains, retrieves entries via the appropriate path, checks for contradictions, and synthesizes a personalized answer.

## KB Entry Schema

```yaml
---
concept: <name>
domain: <domain>
confidence: 0.0–1.0
summary: <one-line summary>
sources: [<url or description>]
last_updated: YYYY-MM-DD
# optional:
contradicts: [{concept: <slug>, detail: <why>}]
extends: [<slug>]
gaps: [<what is missing>]
---
```

## CLI

```bash
# Ingest a single note
python3 process.py ingest pipeline/notes/my-note.md

# Ingest all unprocessed notes
python3 process.py ingest --all

# Validate all KB entries against the schema
python3 process.py lint

# Regenerate INDEX.md from disk
python3 process.py rebuild-index

# Rebuild ChromaDB vector index (run after bulk ingests)
python3 process.py rebuild-vector-index

# Semantic search
python3 process.py query "ejercicios para escoliosis" --domain fisioterapia --n-results 10
```

## Setup

```bash
pip install -r requirements.txt
```

Requires a `GROQ_API_KEY` environment variable (supports `GROQ_API_KEY_2`, `GROQ_API_KEY_3` for key rotation).

## Dependencies

- `chromadb` — local vector store
- `sentence-transformers` — multilingual embeddings
- `python-frontmatter` — YAML frontmatter parsing
- `groq` — LLM extraction (Llama 3.3 70B)
