# Feature Landscape

**Domain:** Personal adaptive knowledge oracle (PKM + AI synthesis + personal context)
**Researched:** 2026-04-08

---

## Table Stakes

Features the system must have or it collapses into "another folder of notes."

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Atomic entry schema | Without a standard schema, Claude can't reliably reason over the KB — every entry becomes its own snowflake | Low | Fields: concept, domain, confidence, sources, contradictions, gaps. One idea per file. |
| Source attribution on every entry | When the oracle answers, provenance matters — especially when sources disagree | Low | Frontmatter field. Can be a list of note filenames. |
| One-line summary per entry | Claude reads summaries to decide relevance before loading full content (Karpathy pattern). Without this, the model loads everything or misses relevant entries | Low | First line of each file after title. Non-negotiable for Claude Code querying. |
| Domain tagging | Required for gap detection ("over X domain there are N entries") and for scoping queries | Low | Frontmatter field. Free-form tags, not a fixed taxonomy. |
| Confidence level per entry | Distinguishes "one influencer said this" from "multiple sources + personal validation" | Low | Scale: LOW / MEDIUM / HIGH. Drives contradiction handling. |
| Ingest pipeline (notes → KB entries) | The pipeline from `notes/*.md` to atomic KB entries must be automated, not manual — otherwise the KB never gets populated | Medium | Already have `transcribe.py`. Need a second step: notes → atomic entries. |
| Reproducibility of ingest | Running ingest twice on the same input must produce stable output, not drift | Low | Idempotent by entry ID (slug or hash of concept + domain). |
| Contradiction flag | When a new entry contradicts an existing one, it must be flagged — not silently overwritten. This is a core differentiator vs. normal note-taking | Medium | Implementation: compare on ingest, write `contradictions:` frontmatter field. |
| Personal context as first-class knowledge | Entries like "Manuel has scoliosis + flat feet" must be queryable and applied during synthesis, not stored in a separate profile file | Low | Same schema as any other entry. Domain: `personal_context`. |
| Claude Code queryability | The oracle interface in MVP — Claude Code reads the KB directory and synthesizes answers. Requires consistent structure and summaries. | Low | Directory structure and naming conventions matter. |

---

## Differentiators

What makes this an oracle, not just a smarter folder of notes.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Contradiction detection on ingest | Most PKM tools ignore conflicts. This system surfaces them explicitly, so the user knows "Source A says X, Source B says the opposite" | Medium | LLM comparison during ingest step. Flag pairs of conflicting entries with links to both. |
| Gap detection | The system knows what it doesn't know. "Over trading you have 3 entries — that's thin." This inverts the usual PKM failure mode where you don't know what's missing. | Medium | Computed at query time or as a periodic audit: count entries per domain, flag domains with <N entries. |
| Personalized synthesis | Answers are filtered through personal context automatically. A query about "exercises for back pain" draws on both the physiotherapy KB entries AND the scoliosis/flat-feet entries — without the user having to specify this every time. | Medium | Claude's context window handles this once entries are co-located in the same KB. |
| Confidence propagation | An answer derived entirely from LOW-confidence entries is flagged as such. The oracle reports its own uncertainty. | Low-Medium | Aggregate confidence in synthesis response. |
| Domain coverage map | On demand: "show me which domains I know well vs. where the KB is thin." Practical audit tool. | Low | Script or Claude Code query over frontmatter. |
| Source quality differentiation | Not all sources are equal. A physiotherapist's structured video ≠ a random Instagram influencer's opinion. Source type can be encoded and influences confidence. | Low | Frontmatter field: `source_type: [expert_video, influencer, personal_experiment, paper]`. |
| KB auto-improvement loop | When the oracle answers and Manuel corrects it, the correction flows back into the KB as a new or updated entry. The system gets smarter with use. | High | MVP: manual correction via CLI. Later: structured feedback entry. |
| Temporal knowledge tracking | Some knowledge becomes outdated (e.g., "in 2023 the consensus on X was Y"). Timestamp + `superseded_by` field allows tracking knowledge evolution. | Low | Frontmatter fields: `created`, `last_updated`, `superseded_by`. Not needed for MVP but schema should accommodate. |

---

## Anti-Features

Things PKM systems routinely build that kill adoption or corrupt the knowledge base.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Hierarchical folder taxonomy | Folders require upfront decisions that are usually wrong. They create filing overhead and lock knowledge into single categories. | Use domain tags + free-form links. No folders below the top-level KB directory. |
| Manual entry creation | If populating the KB requires human effort per entry, it won't happen. The system will stall at ~20 entries. | Automate: `notes/*.md` → atomic KB entries via LLM ingest script. Human reviews output, doesn't write it. |
| Rich text / WYSIWYG format | Non-plain-text formats break portability, make diffs unreadable, and create tool lock-in. | Plain markdown only. Frontmatter for structured fields. |
| Separate "user profile" | Splitting personal context into a profile breaks the oracle's holistic reasoning. Manuel's scoliosis is relevant to physiotherapy AND sports AND travel queries. | Personal context = KB entries with `domain: personal_context`. The LLM finds them naturally. |
| Bidirectional link maintenance | Manually maintaining backlinks is overhead that will be abandoned. | Forward links in `related:` frontmatter are enough. Claude doesn't need backlinks to navigate — it reads everything. |
| Versioning / changelog per entry | For a personal KB this size, tracking every edit is noise. | `last_updated` timestamp only. If an entry is superseded, write a new one with `superseded_by:` pointing to old. |
| Spaced repetition / review loops | This system is an oracle, not a study tool. SRS adds friction and a separate workflow that competes with using the KB. | Omit entirely. Retrieval happens at query time, not on schedule. |
| Mandatory tags/categories on ingest | If every ingested note requires human classification, it becomes a bottleneck. | Let the ingest LLM propose domain + tags. Human can override but doesn't have to. |
| Semantic search / vector DB at MVP scale | ChromaDB or similar adds infra complexity without proportional benefit until the corpus exceeds ~100-200 entries. | Plain-text scan + Claude context window is sufficient. Re-evaluate when corpus > 150 entries. |
| "Perfect system" perfectionism | The #1 PKM failure mode: more time refining the system than using it. Schema ossification, taxonomy debates, etc. | Ship minimal schema. Add fields only when a concrete need is blocked by their absence. |

---

## Feature Dependencies

```
Atomic entry schema
  → Ingest pipeline (needs schema to write to)
  → Contradiction detection (needs schema to compare)
  → Gap detection (needs domain tags from schema)
  → Confidence propagation (needs confidence field from schema)
  → Claude Code queryability (needs one-line summary from schema)

Ingest pipeline
  → Contradiction detection (must run during ingest to flag conflicts)
  → Personal context as first-class knowledge (context enters via ingest)

Contradiction detection
  → Confidence propagation (conflicting entries lower answer confidence)

Domain tagging
  → Gap detection (counts per domain)
  → Domain coverage map (aggregates domain tags)

Source attribution
  → Source quality differentiation (attribution is prerequisite)
  → Confidence propagation (source quality feeds confidence)
```

---

## MVP Recommendation

Prioritize in order:

1. **Atomic entry schema** — everything else is blocked without this
2. **Ingest pipeline** (`notes/*.md` → KB entries) — the KB is empty without it
3. **Contradiction detection on ingest** — core value prop, and easier to build now than retrofit
4. **One-line summary + domain tag + confidence** — required for Claude Code querying to work well
5. **Personal context entries** — add Manuel's known context as KB entries from day one

Defer:
- Domain coverage map: easy to add once KB has >20 entries — implement when useful
- KB auto-improvement loop: manual correction is fine for MVP
- Temporal tracking (`superseded_by`): design the schema field now, don't implement logic yet
- Source quality differentiation: include `source_type` in schema, ignore in queries until corpus is richer

---

## Sources

- Karpathy LLM Wiki pattern: [MindStudio breakdown](https://www.mindstudio.ai/blog/andrej-karpathy-llm-wiki-knowledge-base-claude-code) / [VentureBeat](https://venturebeat.com/data/karpathy-shares-llm-knowledge-base-architecture-that-bypasses-rag-with-an) — HIGH confidence (author is Karpathy himself)
- Zettelkasten atomicity principles: [zettelkasten.de](https://zettelkasten.de/atomicity/guide/) — HIGH confidence (canonical source)
- PKM anti-patterns / productivity trap: [Medium - PKM Trap](https://medium.com/@paralloid/the-pkm-trap-when-productivity-becomes-procrastination-669e03de9c11) / [PKM Paradox](https://medium.com/@helloantonova/the-pkm-paradox-why-most-knowledge-management-tools-fail-to-meet-our-needs-d5042f08f99e) — MEDIUM confidence (community wisdom, consistent across multiple sources)
- Knowledge graph contradiction handling: [Milvus reference](https://milvus.io/ai-quick-reference/how-do-you-ensure-data-consistency-in-a-knowledge-graph) — MEDIUM confidence
- PKM tool landscape: [Obsidian vs Logseq comparison 2025](https://www.glukhov.org/post/2025/11/obsidian-vs-logseq-comparison/) — MEDIUM confidence
