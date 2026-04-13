# Phase 3: Oracle Interface - Research

**Researched:** 2026-04-13
**Domain:** CLAUDE.md prompt engineering, KB navigation, Claude Code context loading
**Confidence:** HIGH

---

## Summary

Phase 3 produces no Python code. The entire deliverable is a `CLAUDE.md` file that instructs Claude Code how to act as a personalized knowledge oracle. When Claude reads this file at session start, it must know: where the KB lives, how to load and filter entries, how to apply personal context automatically, how to detect and surface gaps, and how to surface contradictions rather than silently resolve them.

The KB currently has 48 concepts in `kb/concepts/` (45 `ia`, 2 `personal`, 1 `psicologia`) and 4 personal context entries in `kb/personal/` (escoliosis, pies planos, perfil-fisico-general, objetivos-fisicos-actuales). The corpus is below 100 — Phase 4 (ChromaDB) is out of scope. Claude reads files directly; there is no vector search, no API call, no script invocation. The oracle mechanism is pure prompt engineering backed by the file system.

The core challenge is specifying a reading strategy that is complete enough to yield correct answers but not so exhaustive that Claude loads the entire KB on every query (context budget). Gap detection requires counting entries per domain and comparing against a threshold — this logic must be specified precisely in `CLAUDE.md`. Contradiction surfacing requires Claude to check the `contradicts` frontmatter field and report both sides.

**Primary recommendation:** Write `CLAUDE.md` as a contract with four sections — KB Layout, Reading Protocol, Behavioral Rules, and Response Template — using imperative language throughout. Claude Code treats `CLAUDE.md` as instructions, not suggestions.

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| KB-05 | The system detects gaps: "sobre X hay N entradas — cobertura escasa" | Gap detection requires counting domain entries at query time. CLAUDE.md must define the threshold (suggested: ≤3 entries = sparse) and mandate reporting before the main answer body. |
| KB-06 | Claude Code can query the KB and return synthesized, personalized answers | CLAUDE.md reading protocol + personal context loading rule + domain declaration rule cover this requirement end-to-end. |
</phase_requirements>

---

## Standard Stack

### Core

| Component | Version / Format | Purpose | Why |
|-----------|-----------------|---------|-----|
| `CLAUDE.md` | Markdown, imperative | Oracle contract — read once per session by Claude Code | Claude Code auto-reads this file on session start; no code, no CLI |
| `kb/concepts/*.md` | YAML frontmatter + markdown body | Domain knowledge entries | Already built in Phase 2 |
| `kb/personal/*.md` | YAML frontmatter + markdown body | Personal context entries | Already built in Phase 1 |
| `kb/INDEX.md` | Markdown table | Domain/slug/path map | Auto-maintained by process.py; enables fast domain filtering |
| `python-frontmatter` | 1.x (already installed) | If any helper script is needed to count entries | Already in the environment |

### No Additional Libraries Needed

Phase 3 is a pure authoring phase. No new dependencies. No new Python modules. No new CLI tools.

---

## Architecture Patterns

### KB Layout (already built — CLAUDE.md must describe it precisely)

```
kb/
├── concepts/         # 48 entries — domain knowledge, flat structure
│   └── *.md          # YAML frontmatter: concept, domain, confidence, summary, sources, last_updated
│                     # Optional: contradicts, extends, gaps
├── personal/         # 4 entries — Manuel's personal context
│   └── *.md          # Same schema, domain: personal
└── INDEX.md          # Slug | Domain | Summary | Path table
```

### Pattern 1: Session Initialization (Zero-Setup Contract)

**What:** CLAUDE.md tells Claude to load all `kb/personal/*.md` entries unconditionally at session start, before any query is posed.
**When to use:** Every session, triggered by reading CLAUDE.md.
**Contract language:**
```
At the start of every session, before answering any question:
1. Read all files in kb/personal/ and hold their content as Manuel's active personal context.
2. Do not wait to be asked — this is mandatory initialization.
```

### Pattern 2: Domain-Filtered Query Protocol

**What:** When a question is received, Claude identifies the relevant domain(s), reads `kb/INDEX.md` to get paths, then reads only the matching concept entries.
**Why domain-filter:** With 48 entries today, full-read is feasible; as corpus grows toward 100, domain-filtered reads stay performant within Claude's context budget.
**Contract language:**
```
When answering a question:
1. Identify the domain(s) from: fisioterapia | ia | finanzas | trading | esoterismo | psicologia | deportes | personal
2. Read kb/INDEX.md to find all entries for those domains.
3. Read each matching concept file.
4. Synthesize an answer that integrates personal context with domain knowledge.
```

### Pattern 3: Gap Detection

**What:** After reading domain entries, count them. If count ≤ threshold, declare coverage as sparse.
**Threshold:** ≤3 entries for a domain = sparse. This is a concrete number CLAUDE.md must specify.
**Why specify the threshold in CLAUDE.md:** Claude will not invent a consistent threshold without one. Without a number, gap reporting will be inconsistent across sessions.
**Contract language:**
```
After loading domain entries, count them.
If count ≤ 3: state "sobre [domain] hay [N] entradas — cobertura escasa" before the main answer.
If count > 3 but < 10: state "sobre [domain] hay [N] entradas".
Always declare the count — never omit it.
```

### Pattern 4: Contradiction Surfacing

**What:** When a concept entry has a `contradicts` field, Claude must report both positions explicitly and never silently resolve the conflict.
**How it works:** The `contradicts` field is already populated by `process.py`'s Pass 2 LLM call. Claude reads it from frontmatter.
**Contract language:**
```
When reading a concept that has a `contradicts` field:
- Read the conflicting entry identified by the slug.
- State both positions in the answer.
- Do NOT pick one side. Surface the conflict explicitly: "Estas dos entradas se contradicen: [A dice X, B dice Y]".
```

### Pattern 5: Domain Declaration

**What:** Every substantive answer must declare which domains and how many entries were consulted.
**Format (specify in CLAUDE.md):**
```
[Domains consultados: fisioterapia (4 entradas), personal (4 entradas)]
```
**Why:** Success criterion 4 requires this to be unprompted and consistent.

### Pattern 6: Response Template

CLAUDE.md must specify a mandatory response structure so behavior is reproducible across sessions:

```
1. Coverage report — domain(s) consulted + entry counts (gap warning if ≤ 3)
2. Personal context applied — list which personal entries were relevant
3. Synthesized answer — integrate domain knowledge with personal context
4. Contradictions (if any) — surface both sides explicitly
5. Gaps in KB (if relevant) — from the `gaps` field of relevant entries
```

### Anti-Patterns to Avoid

- **Loading ALL concepts always:** Context budget problem. Always domain-filter via INDEX.md first.
- **Silently resolving contradictions:** The `contradicts` field exists precisely to be surfaced. Never pick a winner.
- **Omitting personal context unless asked:** Personal context is loaded unconditionally — it is not optional context.
- **Vague gap language:** "Hay poca información" without a count violates KB-05. Always include the number.
- **Skipping the domain declaration:** Every answer must declare domains consulted, even for simple questions.
- **CLAUDE.md as suggestions:** Language must be imperative ("must", "always", "never"), not advisory ("should", "try to").

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Entry counting for gap detection | Custom script | Claude counts inline while reading INDEX.md | No runtime infra needed at this corpus size |
| Semantic search for relevant entries | Vector index (Phase 4) | Domain filter via INDEX.md + direct file read | Below 100-entry threshold; Phase 4 explicit deferral |
| Personal context injection | Pre-processing pipeline | CLAUDE.md mandatory init rule | Claude can read files directly — no middleware |
| Contradiction graph | Graph DB or custom tracker | `contradicts` frontmatter field | Already populated by process.py |

**Key insight:** At 48 entries, the oracle is entirely a Claude Code prompt engineering problem. Infrastructure is overkill and was explicitly deferred to Phase 4.

---

## Common Pitfalls

### Pitfall 1: Ambiguous Reading Instructions

**What goes wrong:** CLAUDE.md says "read relevant KB entries" without specifying how to identify relevance. Claude guesses based on keywords and misses entries or reads too many.
**Why it happens:** Prompt engineering without concrete algorithms.
**How to avoid:** Specify the exact algorithm — (1) determine domain, (2) read INDEX.md, (3) read all entries in matching domain. No ambiguity.
**Warning signs:** Answers that miss obvious relevant entries, or answers that reference entries from wrong domains.

### Pitfall 2: Gap Threshold Not Specified

**What goes wrong:** Without a numeric threshold, Claude will inconsistently decide what "escasa cobertura" means. One session says 5 entries is sparse, another says 2.
**Why it happens:** Claude infers thresholds contextually if not given.
**How to avoid:** Hard-code the threshold in CLAUDE.md (e.g., ≤3 entries = sparse). One number, stated once.

### Pitfall 3: Contradiction Detection Depends on LLM Quality — Not Guaranteed

**What goes wrong:** The `contradicts` field is populated by `process.py`'s Pass 2 LLM call, which is best-effort (returns [] on RateLimitError). Some genuine contradictions may not be flagged in frontmatter.
**Why it happens:** Rate limiting or LLM judgment errors in process.py at ingestion time.
**How to avoid:** CLAUDE.md should instruct Claude to also do a light cross-check: "if two entries in the same domain make conflicting claims in their summaries, surface this even if `contradicts` is absent." This adds a safety net.
**Warning signs:** Success criterion 3 fails because contradictions in KB weren't caught by process.py.

### Pitfall 4: Personal Context Not Applied Unless Explicitly Named

**What goes wrong:** Claude answers "qué ejercicios para escoliosis" with generic advice, not mentioning pies planos (which is also relevant to exercise selection).
**Why it happens:** Without explicit instruction to cross-apply all personal context, Claude only applies directly named conditions.
**How to avoid:** CLAUDE.md must say: "For every answer, check ALL personal context entries for relevance, not just the one named in the question."

### Pitfall 5: CLAUDE.md Doesn't Survive Fresh Sessions

**What goes wrong:** CLAUDE.md instructions work in the current session because Claude remembers prior context, but fail in a truly fresh session.
**Why it happens:** Relying on implied context rather than explicit self-contained instructions.
**How to avoid:** Write CLAUDE.md as if Claude has zero prior knowledge of this project. Include the full KB path, the full domain enum, the full response template. Test by starting a fresh Claude Code session with no history.

### Pitfall 6: INDEX.md Out of Sync

**What goes wrong:** INDEX.md only has the 4 personal entries (as of now) — the 48 concepts in `kb/concepts/` are not listed in INDEX.md yet. The oracle protocol that relies on INDEX.md for domain filtering will miss all concepts.
**Why it happens:** process.py writes concepts but the `<!-- Entries below are managed by process.py -->` section in INDEX.md is currently empty. INDEX.md was not updated during Phase 2 batch ingest.
**How to avoid:** Phase 3 must include a task to either (a) update INDEX.md with all 48 existing concepts, or (b) instruct CLAUDE.md to fall back to direct `kb/concepts/` glob when INDEX.md is incomplete. Option (a) is cleaner — process.py should be extended to write INDEX.md entries, or a one-time backfill script run.
**Warning signs:** Oracle returns "no entries found" for `ia` domain despite 45 existing concept files.

---

## Code Examples

### CLAUDE.md Skeleton (reference structure for planner)

```markdown
# Second Brain — Oracle Interface

## KB Layout
- kb/concepts/  — domain knowledge (flat, N entries)
- kb/personal/  — Manuel's personal context (4 entries)
- kb/INDEX.md   — slug | domain | summary | path

Domains: fisioterapia | ia | finanzas | trading | esoterismo | psicologia | deportes | personal

## Session Initialization (MANDATORY)
At the start of every session, before any question:
1. Read every file in kb/personal/ — this is Manuel's active personal context.
2. Confirm initialization silently — do not announce it unless asked.

## Query Protocol
When Manuel asks a question:
1. Identify relevant domain(s).
2. Read kb/INDEX.md — collect all entries for those domains.
3. Read each concept file listed.
4. Check every loaded concept for a `contradicts` field.

## Gap Detection
After loading domain entries, count them:
- ≤ 3 entries → state: "sobre [domain] hay [N] entradas — cobertura escasa"
- > 3 entries → state: "sobre [domain] hay [N] entradas"
Always report the count before the main answer.

## Contradiction Rule
If a loaded concept has a `contradicts` field, or if two summaries make mutually exclusive claims:
- Read both conflicting entries.
- State both positions explicitly.
- Never pick a winner or silently synthesize.

## Response Structure (mandatory order)
1. [Dominios consultados: X (N entradas), Y (M entradas)] — with gap warning if applicable
2. [Contexto personal aplicado: list of relevant personal entries]
3. Answer body — synthesized, concrete, personalized
4. Contradictions (if any) — explicit, not resolved
5. Gaps from entries (if relevant) — from `gaps` field
```

### Checking contradicts field (Python — for verification tests only)

```python
import frontmatter
from pathlib import Path

def get_contradicting_entries(kb_dir: Path) -> list[dict]:
    """Return all entries that have a contradicts field populated."""
    result = []
    for p in kb_dir.glob("*.md"):
        post = frontmatter.load(str(p))
        if post.metadata.get("contradicts"):
            result.append({
                "concept": post.metadata["concept"],
                "contradicts": post.metadata["contradicts"],
            })
    return result
```

### Backfill INDEX.md (one-time task for Phase 3)

```python
# Source: project codebase — process.py pattern
import frontmatter
from pathlib import Path

def rebuild_index(concepts_dir: Path, personal_dir: Path, index_path: Path) -> None:
    rows = []
    for kb_dir in [personal_dir, concepts_dir]:
        for p in sorted(kb_dir.glob("*.md")):
            post = frontmatter.load(str(p))
            m = post.metadata
            rows.append((m.get("concept",""), m.get("domain",""), m.get("summary",""), str(p)))
    
    header = "| Slug | Domain | Summary | Path |\n|------|--------|---------|------|\n"
    body = "\n".join(f"| {r[0]} | {r[1]} | {r[2]} | {r[3]} |" for r in rows)
    index_path.write_text(f"# Knowledge Base Index\n\n{header}{body}\n\n<!-- Entries below are managed by process.py -->\n")
```

---

## State of the Art

| Old Approach | Current Approach | Notes |
|--------------|-----------------|-------|
| Separate user-profile store | Personal context entries in KB (same schema, domain: personal) | Phase 1 decision — enables uniform reading |
| Session setup every time | CLAUDE.md read once at session start | Zero-setup contract |
| Manual contradiction check | `contradicts` field in frontmatter, populated at ingest | Phase 2 decision |
| Full KB load on every query | Domain-filter via INDEX.md first | Context budget protection |
| ChromaDB semantic search | Direct file reads | Deferred to Phase 4 (>100 entry threshold) |

---

## Open Questions

1. **INDEX.md is currently empty for the 48 concepts in kb/concepts/**
   - What we know: INDEX.md only lists 4 personal entries. The `<!-- Entries below are managed by process.py -->` separator exists but nothing was written below it during batch ingest.
   - What's unclear: Was INDEX.md update intentionally deferred, or is it a gap in Phase 2?
   - Recommendation: Phase 3 Wave 0 must include a task to backfill INDEX.md with all 48 concept entries. Two options: (a) extend process.py with an `index-rebuild` subcommand, or (b) one-time script. Either is fine — the INDEX.md must be populated before the oracle protocol can use it for domain filtering.

2. **Contradiction LLM quality — 1 entry found with spurious self-reference**
   - What we know: `model-swapping-in-claude-code` has a `contradicts` entry pointing to `claude-as-a-shell` with the detail "no direct logical conflicts" — the LLM flagged it anyway. The CLAUDE.md contradiction rule must handle false positives gracefully.
   - Recommendation: Instruct Claude to read the conflicting entry and make its own judgment before surfacing. "If the contradicts field is populated but the two entries say the same thing, skip — do not report false conflicts."

3. **Domain coverage is heavily skewed to `ia` (45/48 concepts)**
   - What we know: Nearly all ingest so far is from the `claude-env` topic, mapping to `ia` domain. The gap detection rule will correctly flag all other domains as sparse.
   - What's unclear: Whether this is working as intended (all notes processed so far are IA-related) or whether domain mapping needs review.
   - Recommendation: Not a Phase 3 concern — gap detection will surface this naturally. Document it as expected behavior.

---

## Validation Architecture

nyquist_validation is enabled (config.json has `"nyquist_validation": true`).

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (existing, configured) |
| Config file | pytest.ini (existing) |
| Quick run command | `cd /home/manuel/Desktop/PROJECTS/SECONDBRAIN && pytest tests/ -m "not integration" -x -q` |
| Full suite command | `cd /home/manuel/Desktop/PROJECTS/SECONDBRAIN && pytest tests/ -x -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| KB-05 | Gap detection: domains with ≤3 entries trigger "cobertura escasa" | manual-only | Requires live Claude Code session; cannot be unit-tested | N/A — human test |
| KB-05 | INDEX.md is populated with all concepts (precondition for KB-05 oracle behavior) | unit | `pytest tests/test_index.py::test_index_contains_all_concepts -x` | ❌ Wave 0 |
| KB-06 | CLAUDE.md exists and contains required sections | unit | `pytest tests/test_claude_md.py::test_claude_md_sections -x` | ❌ Wave 0 |
| KB-06 | All personal context files are readable and valid | unit | `pytest tests/test_lint.py` (existing — covers kb/personal) | ✅ exists |
| KB-06 | Contradicts field entries are populated in at least one concept | unit | `pytest tests/test_contradiction.py` (existing — covers field presence) | ✅ exists |

**Note on KB-05 and KB-06 oracle behavior:** The oracle's actual response quality (personalization, gap reporting, contradiction surfacing) can only be validated in a live Claude Code session. These are human-verified success criteria, not automated tests.

### Sampling Rate

- **Per task commit:** `pytest tests/ -m "not integration" -x -q`
- **Per wave merge:** `pytest tests/ -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`, plus human validation of success criteria in fresh Claude Code session

### Wave 0 Gaps

- [ ] `tests/test_claude_md.py` — checks CLAUDE.md exists and contains required sections (KB Layout, Session Initialization, Query Protocol, Gap Detection, Contradiction Rule, Response Structure)
- [ ] `tests/test_index.py` — checks INDEX.md contains entries for all .md files in kb/concepts/ and kb/personal/ (precondition for oracle domain-filter protocol)

---

## Sources

### Primary (HIGH confidence)

- Direct inspection of `/home/manuel/Desktop/PROJECTS/SECONDBRAIN/process.py` — full understanding of what contradicts field contains and how it's populated
- Direct inspection of `kb/concepts/*.md` (48 entries) and `kb/personal/*.md` (4 entries) — corpus state confirmed
- Direct inspection of `kb/INDEX.md` — confirmed it only has 4 personal entries, missing all 48 concepts
- `.planning/ROADMAP.md`, `.planning/REQUIREMENTS.md`, `.planning/STATE.md` — phase scope and decisions confirmed
- `.planning/config.json` — nyquist_validation confirmed enabled

### Secondary (MEDIUM confidence)

- Claude Code CLAUDE.md behavior: based on established pattern that Claude Code reads CLAUDE.md at session start and treats its contents as operative instructions. This is the mechanism the entire project is built on.

### Tertiary (LOW confidence)

- Gap detection threshold (≤3 entries = sparse): judgment call. No authoritative source. Chosen because with 48 entries across 8 domains, most non-ia domains have 0-2 entries and a threshold of 3 correctly identifies them as sparse.

---

## Metadata

**Confidence breakdown:**
- KB structure and corpus state: HIGH — direct file inspection
- CLAUDE.md authoring pattern: HIGH — project design pattern confirmed across phases
- Gap detection threshold: LOW — arbitrary judgment, needs validation
- Contradiction surfacing via frontmatter: HIGH — field exists in at least one entry, mechanism confirmed
- INDEX.md gap: HIGH — confirmed by direct inspection

**Research date:** 2026-04-13
**Valid until:** 2026-05-13 (stable — no external dependencies)
