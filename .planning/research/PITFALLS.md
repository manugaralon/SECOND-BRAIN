# Domain Pitfalls: Personal KB Oracle / Second Brain / RAG

**Domain:** Personal adaptive knowledge base with social media ingestion and LLM query interface
**Researched:** 2026-04-08
**Confidence:** HIGH (verified via Karpathy LLM Wiki gist, RAG research, PKM failure pattern literature)

---

## Critical Pitfalls

Mistakes that cause rewrites, system abandonment, or permanent data corruption.

---

### Pitfall 1: Hallucination Embedding — Permanent False Facts

**What goes wrong:** When the LLM synthesizes raw source content into KB entries, a hallucination gets written as a fact. Because entries are then cross-referenced by other entries, the false fact propagates and reinforces itself. On query, Claude reads the entry and treats it as verified knowledge. The permanence of .md files turns a one-time generation error into a permanent feature of the KB.

**Why it happens:** The ingest pipeline trusts LLM output without a verification gate. Social media content is already low-quality signal — physiotherapy reels, finance tips — and the LLM will confidently synthesize confidently wrong content.

**Consequences:** The oracle gives wrong, personalized advice. Worse: it cites "sources" (your KB entries) that themselves contain the error, making the output look well-supported.

**Warning signs:**
- KB entries that have no `fuentes` field or a single low-credibility source
- Entries that were written in one pass and never updated
- The oracle gives answers that feel authoritative but can't be traced to original source content

**Prevention:**
- Every entry gets a `confianza` field: `baja` (single source, unverified), `media` (multiple sources agree), `alta` (verified across sources)
- Ingest pipeline outputs entries as `confianza: baja` by default — never promoted automatically
- Contradicting entries flag each other explicitly, not silently reconciled
- Phase 1 (schema design) must encode this before any content enters the KB

**Phase that must address it:** Phase 1 (KB schema) and Phase 2 (ingest pipeline)

---

### Pitfall 2: Schema Drift — Entries Become Incomparable Over Time

**What goes wrong:** Early entries are written with one schema (`concepto`, `dominio`, `confianza`). After a month, a new field seems useful (`aplicación_personal`). Six months in, half the entries have it, half don't. The KB becomes a heterogeneous mess that Claude can't reason over consistently. Queries for "what applies to my condition" fail because the field doesn't exist on older entries.

**Why it happens:** Schema evolves during use. Without a single canonical schema document and a migration protocol, each ingest session slightly diverges.

**Consequences:** Query reliability degrades over time. You can't do consistent gap detection or contradiction checking across entries that don't share a common structure.

**Warning signs:**
- Fields present on some entries but absent on others
- The schema in CLAUDE.md or a config file has drifted from the actual entries on disk
- Gap detection script finds "no field X" on 40% of entries

**Prevention:**
- A single canonical `schema.md` (or CLAUDE.md section) defines every field, its type, and whether it's required or optional
- When schema changes, a migration script updates existing entries (even if just to add `field: null`)
- Schema changes require explicit decision, not organic drift
- Keep the schema minimal: only fields that improve queries. Every optional field is a future inconsistency.

**Phase that must address it:** Phase 1 (KB schema design) — lock this before writing any entries

---

### Pitfall 3: The Collection Trap — More Content, Worse Oracle

**What goes wrong:** Every Instagram reel gets ingested. The KB grows to 500+ entries. Claude reads all of them (or retrieves top-K) and the quality of answers degrades because low-signal content drowns high-signal content. The "Lost in the Middle" effect means Claude misses critical entries when the context is noisy.

**Why it happens:** Ingesting feels productive. The barrier to "add this to the KB" is low. There's no active curation gate that asks "does this improve the KB or just add noise?"

**Consequences:** The oracle becomes less useful as it grows — the opposite of what a KB should do. Retrieval surfaces irrelevant entries. Synthesis quality drops.

**Warning signs:**
- Multiple entries on the same concept that don't reference each other
- Entries with `confianza: baja` that have never been updated or merged
- The corpus has grown but query quality has stayed flat or regressed

**Prevention:**
- Ingest creates a candidate entry, not a permanent one — review gate before committing to KB
- Duplicate detection at ingest time: "Entry on `escoliosis + respiración` already exists — merge or create separate?"
- Curate, don't hoard: if an entry doesn't add information not already in the KB, discard it
- At ~50 entries, run a deliberate audit: merge, promote, prune

**Phase that must address it:** Phase 2 (ingest pipeline) — build the review gate before the corpus grows

---

### Pitfall 4: Contradiction Handling Complexity Trap

**What goes wrong:** You design a full contradiction graph — entries reference each other as contradicting sources, each contradiction has a resolution status, you track which source is more credible. The system becomes so complex that maintaining it takes longer than the knowledge is worth. You stop ingesting because every new entry might create unresolvable contradictions.

**Why it happens:** Contradiction tracking is genuinely hard. The temptation is to build a proper system upfront. But a complex contradiction model adds overhead to every ingest and query operation.

**Consequences:** The ingest pipeline stalls. The contradiction backlog grows. The KB freezes.

**Warning signs:**
- Ingest takes >15 minutes per item because of contradiction resolution
- There's a growing list of "unresolved contradictions" that nobody reviews
- The complexity of the contradiction model exceeds the value of the KB

**Prevention:**
- Contradiction handling must be minimal and non-blocking: flag it, don't resolve it automatically
- Minimal viable contradiction model: an entry has an optional `contradice: [entry_id]` field and a note explaining the conflict. That's it.
- Resolution is a human decision, never automated
- The oracle surfaces contradictions on query ("nota: hay contradicción sobre este punto") without hiding them
- Do not build a contradiction graph in Phase 1 — add it only when contradictions actually appear

**Phase that must address it:** Phase 1 (schema) — design the field but keep it optional and simple

---

## Moderate Pitfalls

---

### Pitfall 5: Context Rot — Personal Context Becomes Misleading

**What goes wrong:** Manuel's personal context (escoliosis stage, current treatment, pain patterns) is ingested as KB entries. Six months later, the condition has changed but the old entries are still in the KB. The oracle now gives advice calibrated to an outdated state. Worse, the old and new entries coexist and contradict each other without a clear "current truth."

**Why it happens:** Personal context is treated like domain knowledge (timeless) when it's actually state (time-bound). There's no mechanism to mark entries as "superseded" or "current as of date X."

**Prevention:**
- Personal context entries get a `fecha_actualización` field and a `vigencia` flag: `actual` / `desactualizado` / `revisión_pendiente`
- When new personal context is ingested, the pipeline checks for conflicting existing entries and prompts for update
- Quarterly review: scan all personal context entries for staleness
- The oracle always includes source dates when answering personal context questions

**Phase that must address it:** Phase 1 (schema) and Phase 3 (query interface) — the oracle must display entry dates

---

### Pitfall 6: The "Too Much Structure" Trap — Frontmatter Overhead

**What goes wrong:** KB entries have 12 frontmatter fields. YAML parsing fails on edge cases. Entries become boilerplate with one real sentence of content. Writing a new entry requires filling a form, not capturing knowledge.

**Why it happens:** Schema design sessions produce comprehensive field lists. Everything seems useful in theory.

**Consequences:** Ingest friction increases. Entries are technically correct but informationally empty. The system becomes a filing system, not a knowledge base.

**Warning signs:**
- Entries where most fields are `null` or `n/a`
- Ingest pipeline produces valid YAML but the content field is two sentences
- You find yourself filling fields "correctly" instead of capturing the actual insight

**Prevention:**
- Maximum 6 required fields: `id`, `concepto`, `dominio`, `confianza`, `fuentes`, `contenido`
- Everything else is optional and only added when actually needed
- Use bold-field metadata in the body (like Karpathy's LLM Wiki) rather than heavy YAML frontmatter — simpler, more readable, less parse failure surface
- The test for a field: "does the query interface use this to filter or rank?" If no, cut it.

**Phase that must address it:** Phase 1 (schema design)

---

### Pitfall 7: RAG Retrieval Failure at Small Scale — The Pre-Mature Vector Store

**What goes wrong:** The project adds ChromaDB or a vector store at 30 entries because "that's how RAG is done." The infrastructure overhead (embedding generation, index maintenance, sync with .md files) outweighs the retrieval benefit at this corpus size. Simple grep/keyword search would have worked better and required zero maintenance.

**Why it happens:** RAG tutorials use vector stores. The pattern feels correct.

**Consequences:** Added complexity, embedding costs, a sync problem between .md canonical files and the vector index, and no measurable retrieval improvement over text search at <100 entries.

**Prevention:**
- The PROJECT.md decision is correct: no vector store until corpus exceeds ~100 entries
- At small scale, Claude reads all relevant files directly — full context is more reliable than retrieval
- If retrieval is needed before 100 entries: BM25/keyword search first, add semantic only when keyword search demonstrably fails
- Index.md with one-line summaries per entry is sufficient for Claude to navigate the KB without embeddings

**Phase that must address it:** Phase 2 (ingest) — explicitly not adding vector infrastructure. Revisit at Phase 4+.

---

### Pitfall 8: Query Interface Becomes the Bottleneck — Friction Kills Use

**What goes wrong:** Querying the KB requires opening a terminal, running a script, specifying the right flags, and knowing the KB structure. After two weeks, queries drop to zero because it's easier to Google. The KB has content but no usage.

**Why it happens:** The query interface is designed for correctness, not for the friction-in-retrieval = friction-in-thought reality. PKM systems consistently fail at recall even when storage is excellent.

**Prevention:**
- The MVP is Claude Code with CLAUDE.md that describes the KB structure — this is already the lowest-friction interface available
- The query interface must require zero setup per session: Claude reads a single index.md to understand the KB, then queries from there
- Design the index.md format specifically for Claude: each entry is one line, with just enough metadata to know whether to fetch the full file
- Measure: if a query takes more than 30 seconds of setup, the interface is broken

**Phase that must address it:** Phase 3 (query interface)

---

## Minor Pitfalls

---

### Pitfall 9: Source Attribution Loss

**What goes wrong:** Entries are synthesized from multiple sources and the original sources are not preserved. Six months later, you can't verify a claim, update it when the source is wrong, or trace what content contributed to a synthesis.

**Prevention:** Every entry includes raw `fuentes` — original URLs, video IDs, post references. Never synthesize without attribution. The `notes/*.md` files from the existing pipeline are the canonical source layer — the KB entries reference them, they don't replace them.

**Phase that must address it:** Phase 2 (ingest pipeline)

---

### Pitfall 10: Domain Bleed — Physiotherapy Advice Mixes With Finance

**What goes wrong:** The oracle gives an answer that mixes physio knowledge and finance knowledge incorrectly because `dominio` is not used as a retrieval filter. The Claude context gets 50 entries from all domains instead of the relevant 10.

**Prevention:**
- `dominio` field is used as a primary filter on query — Claude reads only the relevant domain's index first
- Cross-domain entries are explicitly tagged as such, not accidentally blended
- The oracle declares which domains it's using in its answer

**Phase that must address it:** Phase 3 (query interface)

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|----------------|------------|
| KB schema design | Over-engineering fields (Pitfall 6) | Max 6 required fields, bold metadata over heavy YAML |
| KB schema design | No confidence model (Pitfall 1) | `confianza` field required from day 1 |
| KB schema design | No staleness model for personal context (Pitfall 5) | `vigencia` and `fecha_actualización` for personal entries |
| Ingest pipeline | Collection trap — no curation gate (Pitfall 3) | Review gate before committing entries |
| Ingest pipeline | Source attribution loss (Pitfall 9) | `fuentes` required, never optional |
| Ingest pipeline | Pre-mature vector store (Pitfall 7) | Explicitly defer until >100 entries |
| Contradiction model | Over-complex contradiction tracking (Pitfall 4) | Optional `contradice` field only, no graph |
| Corpus growth | Schema drift over time (Pitfall 2) | Canonical `schema.md`, migration protocol |
| Query interface | High query friction abandonment (Pitfall 8) | Index.md as navigation layer, zero per-session setup |
| Query interface | Domain bleed in retrieval (Pitfall 10) | `dominio` as primary filter |
| Scale transition (~100 entries) | Wrong time to add vector store | Add only when keyword search demonstrably fails |

---

## Sources

- Karpathy LLM Wiki gist: https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f (HIGH confidence)
- RAG pitfalls at scale: https://www.kapa.ai/blog/rag-best-practices (MEDIUM confidence)
- PKM failure analysis: https://medium.com/@ann_p/your-second-brain-is-broken-why-most-pkm-tools-waste-your-time-76e41dfc6747 (MEDIUM confidence)
- RAG noise and degradation 2025: https://ragflow.io/blog/rag-review-2025-from-rag-to-context (MEDIUM confidence)
- Staleness and outdated KB entries: https://shelf.io/blog/outdated-knowledge-base/ (MEDIUM confidence)
- RAG contradiction detection: https://arxiv.org/html/2504.00180v1 (MEDIUM confidence)
- Context rot: https://www.producttalk.org/context-rot/ (MEDIUM confidence)
- Small-scale RAG vs text search: https://www.firecrawl.dev/blog/best-chunking-strategies-rag (MEDIUM confidence)
