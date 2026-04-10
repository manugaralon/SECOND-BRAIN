# Phase 02: Knowledge Processor - Research

**Researched:** 2026-04-10
**Domain:** Python CLI tool — LLM-driven extraction, schema validation, idempotency, contradiction detection
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **Extraction granularity:** Atomic per concept — one KB entry per concept extracted, not one per source note. A carousel with 6 patterns → 6 separate `kb/concepts/*.md` entries. Each entry's `sources` field points back to the originating note slug.
- **Manual intervention on low-confidence extraction:** When the processor cannot confidently identify a clean concept, it pauses and asks for confirmation before writing. Interactive prompt: write / skip / edit concept name. Non-interactive mode flag (`--no-confirm`) available for batch runs — logs uncertain entries instead.
- **Upstream pipeline is read-only:** `transcribe.py` must not be modified. `process.py` reads from `notes/` as its only coupling point.

### Claude's Discretion
- Idempotency mechanism: `processed.log` file tracking processed note slugs
- Contradiction detection: LLM comparison of new entry against existing `kb/concepts/*.md` entries with same domain
- CLI structure: `process.py ingest <file>`, `process.py ingest --all`, `process.py lint`
- Log format: plain text or JSONL, one line per operation
- Confidence threshold value for "low confidence" pause
- Whether `kb/INDEX.md` is updated by process.py in Phase 2

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| KB-01 | El sistema ingiere links (Instagram reels, posts, carruseles) y los convierte en notas .md estructuradas | Notes already exist as `notes/*.md`; process.py is the downstream consumer that converts them into KB entries |
| KB-04 | El sistema detecta cuando nueva información contradice conocimiento existente y lo señala explícitamente | LLM comparison pass against existing `kb/concepts/` entries; populate `contradicts` field + emit log line |
| KB-07 | El flujo ingest → KB es reproducible y fácil de ejecutar cuando llegan nuevos links | `processed.log` idempotency + `--no-confirm` flag + `process.py ingest --all` enable fully reproducible batch runs |
</phase_requirements>

---

## Summary

Phase 2 builds `process.py`: a Python CLI that reads upstream notes from `/home/manuel/Desktop/PROJECTS/IMPENV/pipeline/notes/` and writes atomic `kb/concepts/*.md` entries that conform to the locked schema. The critical design challenge is the 1→N extraction — one note may yield multiple KB entries, requiring an LLM to identify distinct concepts and assign confidence scores.

The LLM tier is constrained to what's available: **Groq** is installed and has an API key set in the environment. Available models include `llama-3.3-70b-versatile` (strong reasoning, good for extraction) and `meta-llama/llama-4-scout-17b-16e-instruct` (already used by transcribe.py for vision). There is no Anthropic SDK installed. All LLM calls go through Groq.

Idempotency is a file-level concern: `processed.log` tracks note slugs already processed. Schema validation uses `python-frontmatter` (already installed, v1.1.0) to read/write YAML frontmatter. Contradiction detection is a second LLM pass that compares a candidate entry's summary against existing entries in the same domain.

**Primary recommendation:** Build process.py as a single-file CLI using `argparse`, `python-frontmatter`, and the `groq` SDK. Two LLM calls per note: one for concept extraction → N entries, one per new entry for contradiction scan against same-domain existing entries.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| python-frontmatter | 1.1.0 (installed) | Read/write YAML frontmatter in KB entries | Already installed; handles round-trip without corrupting YAML |
| groq | 1.1.2 (installed) | LLM API calls for extraction + contradiction | Only LLM SDK installed; GROQ_API_KEY confirmed in env |
| argparse | stdlib | CLI subcommands (ingest, lint) | No dependencies; sufficient for this interface |
| pathlib | stdlib | File paths and glob traversal | Cleaner than os.path for all file operations |
| json / JSONL | stdlib | processed.log format | Zero dependencies; grep-friendly; one record per line |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| PyYAML | bundled with python-frontmatter | YAML serialization | Implicitly used; do not call directly |
| dataclasses | stdlib | Internal data model for extracted concept | Keeps extraction output typed before writing to disk |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| groq (llama-3.3-70b) | anthropic claude | Anthropic SDK not installed; would require pip install + API key setup — out of scope for this phase |
| JSONL for processed.log | plain text one-slug-per-line | JSONL enables richer metadata (timestamp, n_entries_created) without parsing complexity |
| argparse subcommands | click / typer | No additional dependencies needed for two subcommands |

**Installation:** Nothing new needed. Both `groq` and `python-frontmatter` are already installed system-wide. If a `requirements.txt` is added to the project, pin:
```
groq==1.1.2
python-frontmatter==1.1.0
```

---

## Architecture Patterns

### Recommended Project Structure

```
SECONDBRAIN/
├── process.py           # single entrypoint, all logic
├── processed.log        # JSONL idempotency log, one line per processed note
├── schema.md            # existing — output contract (read-only)
├── kb/
│   ├── concepts/        # written by process.py — domain knowledge entries
│   ├── personal/        # existing manual entries — not touched by process.py
│   └── INDEX.md         # Phase 2: NOT updated by process.py (manual for now)
```

### Pattern 1: Two-Pass LLM Extraction

**What:** First pass extracts N concept stubs from the note. Second pass (per entry) checks for contradictions against same-domain existing entries.

**When to use:** Always. Separation keeps prompts focused and avoids hallucination from a single overloaded prompt.

**Extraction prompt contract (input → output):**
```python
# Pass 1: concept extraction
# Input: full note markdown body + frontmatter
# Output: JSON array of concept objects
# Each object: {concept_slug, summary, domain, confidence, gaps: []}
# model: "llama-3.3-70b-versatile"
# response_format: {"type": "json_object"}

system_prompt = """
You are a knowledge extraction engine. Given a note, identify all distinct, 
atomic concepts it teaches. For each concept output:
- concept: kebab-case slug (unique identifier)
- summary: one sentence asserting what this entry states
- domain: one of [fisioterapia, ia, finanzas, trading, esoterismo, psicologia, deportes, personal]
- confidence: float 0.0-1.0 (see scale below)
- gaps: list of strings for unknowns (can be empty)

Confidence scale:
- 0.9+: multiple independent sources agree, no contradictions
- 0.7-0.9: single high-quality source or multiple weak sources
- 0.5-0.7: contested, single influencer, or unverified claim
- below 0.5: explicitly contradicted or speculative

Output JSON: {"concepts": [...]}
"""
```

**Contradiction pass contract:**
```python
# Pass 2: contradiction check (one call per new entry)
# Input: new entry summary + list of existing same-domain entry summaries
# Output: JSON {contradicts: [{concept, detail}] or []}
# Only call if same-domain entries exist

system_prompt = """
You are a contradiction detector. Given a new KB entry and a list of existing 
entries in the same domain, identify any entries that this new entry directly 
contradicts (not merely extends or adds nuance to).
Output JSON: {"contradicts": [{"concept": "slug", "detail": "what conflicts"}]}
Output empty array if no contradictions found.
"""
```

### Pattern 2: Idempotency via JSONL Log

**What:** `processed.log` at project root. One JSON line per processed note. Before any write, check if note slug exists in log.

**Format:**
```json
{"slug": "claude-env_20260407_113900", "processed_at": "2026-04-10T14:30:00", "entries_created": 3, "entries_skipped": 1, "status": "ok"}
```

**Lookup:** Load log at startup into a set of slugs. O(1) check. Re-running `ingest --all` skips already-logged slugs without touching them.

### Pattern 3: Interactive Confirmation Flow

**What:** When extracted concept has `confidence < 0.5` (threshold is discretion), show the proposed entry and prompt for action.

```
Low confidence (0.42): prompting-chain-of-thought
Summary: Chain of thought prompting improves reasoning by instructing the model to think step by step
Domain: ia

  [w] Write as-is
  [s] Skip this entry
  [r] Rename concept slug
  [q] Quit

Choice [w/s/r/q]:
```

**`--no-confirm` behavior:** Skip the pause. Log the low-confidence entry with `status: "skipped_low_confidence"` in processed.log. Never write to kb/concepts/.

### Pattern 4: Lint Subcommand

**What:** `python process.py lint` validates all `kb/concepts/*.md` files against schema rules.

**Checks:**
1. All 6 required fields present (`concept`, `domain`, `confidence`, `summary`, `sources`, `last_updated`)
2. `domain` is one of the 8 valid values
3. `confidence` is float in [0.0, 1.0]
4. `sources` is a non-empty list where each item has either `note` or `url` key, plus `date`
5. `last_updated` is a valid YYYY-MM-DD string
6. `concept` slug matches the filename (without `.md`)
7. Optional fields: if `contradicts` present, each item has `concept` + `detail`; if `extends` present, each item has `concept`

**Output:** One line per violation: `[ERROR] kb/concepts/foo.md: missing required field 'confidence'`

### Anti-Patterns to Avoid

- **Writing index/metadata directly in LLM call:** Always round-trip through `python-frontmatter` — never string-concatenate YAML manually.
- **Loading all existing entries into one LLM context:** Only load same-domain entries for contradiction check. Loading 100+ entries per call wastes tokens and hits context limits.
- **Mutation of source notes:** `notes/` is read-only. process.py must never write there.
- **1:1 mapping assumption:** The extractor must always consider that a note may contain 0, 1, or N concepts. Zero concepts (e.g., pure self-promotion image) is a valid outcome — log as `status: "no_concepts_found"`.
- **Empty optional fields:** Schema explicitly says "do not write empty arrays". The lint check must flag `contradicts: []` as a violation.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| YAML frontmatter parse/write | Custom regex parser | `python-frontmatter` | Handles encoding, multi-line strings, special chars, round-trip fidelity |
| Schema field validation | Custom validator class | Inline checks in lint() function | Schema is small (6 fields + 3 optional groups) — a full validator framework is overkill |
| LLM JSON parsing | Regex extraction | `response_format={"type": "json_object"}` + `json.loads()` | Groq supports JSON mode; avoids brittle text parsing |

**Key insight:** The hard problem in this phase is prompt engineering, not infrastructure. Invest time in the extraction prompt, not in tooling.

---

## Common Pitfalls

### Pitfall 1: LLM Invents Concept Slugs That Collide

**What goes wrong:** Two different notes yield a concept with the same slug (e.g., both produce `prompting-basics`). Second write silently overwrites the first.

**Why it happens:** LLM normalizes similar concepts to the same slug without knowing what's already in `kb/concepts/`.

**How to avoid:** Before writing any entry, check if `kb/concepts/{slug}.md` exists. If it does, either merge sources (extend the existing entry) or use a qualifier suffix (`prompting-basics-v2` is wrong — instead prompt LLM to differentiate). For Phase 2: treat collision as a conflict to surface, not silently overwrite.

**Warning signs:** `kb/concepts/` entry count < expected from processed notes count.

### Pitfall 2: Groq JSON Mode Requires Correct Model

**What goes wrong:** `response_format={"type": "json_object"}` throws an API error on models that don't support it.

**Why it happens:** Not all Groq models support JSON mode. `llama-3.3-70b-versatile` does. `llama-3.1-8b-instant` may not.

**How to avoid:** Use `llama-3.3-70b-versatile` for extraction (supports JSON mode, confirmed). Test JSON mode call explicitly in Wave 0.

**Warning signs:** `groq.BadRequestError: json_object response_format not supported`.

### Pitfall 3: `processed.log` Race Condition on Partial Run

**What goes wrong:** process.py writes `processed.log` entry before all N entries are written. If interrupted mid-note, the note is marked done but some entries were never created.

**Why it happens:** Log entry written optimistically at start of note processing.

**How to avoid:** Write `processed.log` entry AFTER all entries for a note have been successfully written to disk. Use a "write to temp, rename" pattern or write at the very end.

### Pitfall 4: Contradiction Prompt False Positives on Complementary Entries

**What goes wrong:** LLM flags "extends" relationships as contradictions. E.g., `escoliosis-lumbar-diagnostico` and `escoliosis-lumbar-restricciones` both touch "lumbar" but don't contradict.

**Why it happens:** Contradiction prompt is too broad. "Talks about the same subject" != "contradicts".

**How to avoid:** Prompt must explicitly distinguish "contradicts" (incompatible claims) from "extends" (adds information). Include an example in the system prompt showing a true contradiction vs a complement. Threshold: only flag contradiction if the new entry's claim is logically incompatible with an existing one.

### Pitfall 5: All 14 Notes Are Same Topic (claude-env / ia)

**What goes wrong:** Contradiction check loads all `kb/concepts/` entries for domain `ia` — which grows quickly and may exceed context limits in later runs.

**Why it happens:** All 14 upstream notes have `topic: claude-env`, which maps to domain `ia`. With N entries per note, `kb/concepts/` for domain `ia` could be 40-100+ entries quickly.

**How to avoid:** For contradiction check, pass only `summary` fields of existing same-domain entries (not full entry bodies). One summary per line, no frontmatter. Keeps context lean.

---

## Code Examples

### Reading an upstream note

```python
# Source: python-frontmatter docs + confirmed installed v1.1.0
import frontmatter
from pathlib import Path

def load_note(path: Path) -> frontmatter.Post:
    return frontmatter.load(str(path))

note = load_note(Path("notes/claude-env_20260407_113900.md"))
note.metadata  # dict with title, url, topic, type, author, etc.
note.content   # markdown body as string
```

### Writing a KB entry

```python
import frontmatter
from datetime import date
from pathlib import Path

def write_kb_entry(concept_slug: str, data: dict, kb_dir: Path) -> Path:
    post = frontmatter.Post("")
    post["concept"] = data["concept"]
    post["domain"] = data["domain"]
    post["confidence"] = data["confidence"]
    post["summary"] = data["summary"]
    post["sources"] = data["sources"]
    post["last_updated"] = date.today().isoformat()
    if data.get("contradicts"):
        post["contradicts"] = data["contradicts"]
    if data.get("gaps"):
        post["gaps"] = data["gaps"]
    post.content = data.get("body", "")
    
    out_path = kb_dir / f"{concept_slug}.md"
    with open(out_path, "w") as f:
        f.write(frontmatter.dumps(post))
    return out_path
```

### Groq extraction call with JSON mode

```python
import json
from groq import Groq

client = Groq()  # reads GROQ_API_KEY from env

def extract_concepts(note_content: str, note_metadata: dict) -> list[dict]:
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
            {"role": "user", "content": f"Note metadata: {json.dumps(note_metadata)}\n\n{note_content}"}
        ],
        temperature=0.1  # low temp for deterministic extraction
    )
    result = json.loads(response.choices[0].message.content)
    return result.get("concepts", [])
```

### Idempotency check

```python
import json
from pathlib import Path

def load_processed_slugs(log_path: Path) -> set[str]:
    if not log_path.exists():
        return set()
    slugs = set()
    with open(log_path) as f:
        for line in f:
            line = line.strip()
            if line:
                record = json.loads(line)
                slugs.add(record["slug"])
    return slugs

def append_processed(log_path: Path, slug: str, n_created: int, status: str):
    record = {
        "slug": slug,
        "processed_at": datetime.now().isoformat(timespec="seconds"),
        "entries_created": n_created,
        "status": status
    }
    with open(log_path, "a") as f:
        f.write(json.dumps(record) + "\n")
```

### Lint validation

```python
import frontmatter
from pathlib import Path

REQUIRED_FIELDS = ["concept", "domain", "confidence", "summary", "sources", "last_updated"]
VALID_DOMAINS = {"fisioterapia", "ia", "finanzas", "trading", "esoterismo", "psicologia", "deportes", "personal"}

def lint_entry(path: Path) -> list[str]:
    errors = []
    post = frontmatter.load(str(path))
    meta = post.metadata
    
    for field in REQUIRED_FIELDS:
        if field not in meta:
            errors.append(f"missing required field '{field}'")
    
    if "domain" in meta and meta["domain"] not in VALID_DOMAINS:
        errors.append(f"invalid domain '{meta['domain']}'")
    
    if "confidence" in meta:
        try:
            c = float(meta["confidence"])
            if not (0.0 <= c <= 1.0):
                errors.append(f"confidence {c} out of range [0.0, 1.0]")
        except (TypeError, ValueError):
            errors.append("confidence must be a float")
    
    expected_slug = path.stem
    if "concept" in meta and meta["concept"] != expected_slug:
        errors.append(f"concept slug '{meta['concept']}' does not match filename '{expected_slug}'")
    
    # Forbidden empty optional arrays
    for opt_field in ["contradicts", "extends", "gaps"]:
        if opt_field in meta and meta[opt_field] == []:
            errors.append(f"empty {opt_field} array not allowed — omit field if not applicable")
    
    return errors
```

---

## Upstream Note Format — Confirmed Structure

All 14 upstream notes share the same format (confirmed by inspection):

**YAML Frontmatter:**
```yaml
title: string
url: string (Instagram URL)
topic: string (e.g. "claude-env")
type: "carousel" | "video"
author: string
images: int (carousels only)
duration: string (videos only)
upload_date: date or empty
processed_date: datetime
tags: list
```

**Body structure (carousel):** `## Contenido extraído (N imagenes)` → per-image sections with `TEXTO VISIBLE`, `CONTENIDO VISUAL`, `MENSAJE PRINCIPAL`

**Body structure (video):** `## Transcripción` → full text transcription

**Key extraction insight:** Carousels are richer (structured per-image content) but noisier (last slide is often a CTA/follow prompt — ignore). Video transcriptions are cleaner prose but may lack structure. The extraction prompt must handle both.

**Topic → Domain mapping:** All 14 notes have `topic: claude-env` → maps to `domain: ia`. The processor needs a mapping table (or let LLM infer domain from content).

---

## State of the Art

| Old Approach | Current Approach | Impact |
|--------------|------------------|--------|
| Parse YAML by hand (string split) | `python-frontmatter` round-trip | No corruption of existing frontmatter |
| One entry per note | N atomic entries per note | Enables selective context loading in Phase 3 |
| Reprocess all notes on each run | `processed.log` idempotency | Safe to run repeatedly; won't create duplicates |

---

## Open Questions

1. **Slug collision on identical concept from two notes**
   - What we know: Two notes about KERNEL prompting framework → same slug `prompting-kernel-framework`
   - What's unclear: Merge sources into existing entry? Append qualifier? Prompt LLM to diff?
   - Recommendation: Treat as "extend existing entry" — add the new note to `sources` list and update `last_updated`. Emit a log line `extended: <slug>`.

2. **Topic → domain mapping**
   - What we know: All 14 current notes have `topic: claude-env`. Future notes may have `topic: trading`, `topic: fisioterapia`, etc.
   - What's unclear: Hard-code a mapping dict or let LLM infer domain from content?
   - Recommendation: Hard-code a mapping dict as primary (deterministic), fall back to LLM inference when topic not in map. Keeps domain consistent for known topics.

3. **Confidence threshold for interactive pause**
   - What we know: Schema defines < 0.5 as "explicitly contradicted or speculative"
   - Recommendation: Use `confidence < 0.5` as the pause threshold. This aligns with schema semantics — below 0.5 means the claim is shaky enough to warrant human review.

4. **`kb/INDEX.md` update in Phase 2**
   - Recommendation: Do NOT update INDEX.md in Phase 2. Keep it manual. Updating index is a side effect that can corrupt it if process.py errors mid-run. Index update belongs in a future `sync` subcommand.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 (confirmed installed) |
| Config file | none — Wave 0 creates `pytest.ini` |
| Quick run command | `python3 -m pytest tests/ -x -q` |
| Full suite command | `python3 -m pytest tests/ -v` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| KB-07 | `ingest <file>` creates valid KB entry | integration | `pytest tests/test_ingest.py::test_single_note_creates_entries -x` | Wave 0 |
| KB-07 | Running `ingest` twice produces no new files | integration | `pytest tests/test_ingest.py::test_idempotency -x` | Wave 0 |
| KB-07 | `ingest --all` processes all 14 notes | integration (slow) | `pytest tests/test_ingest.py::test_batch_all_notes -x -m integration` | Wave 0 |
| KB-07 | `--no-confirm` skips low-confidence without pause | integration | `pytest tests/test_ingest.py::test_no_confirm_flag -x` | Wave 0 |
| KB-04 | `contradicts` field populated when conflict detected | integration | `pytest tests/test_contradiction.py::test_contradiction_detected -x` | Wave 0 |
| KB-04 | Contradiction logged in processed.log | integration | `pytest tests/test_contradiction.py::test_contradiction_logged -x` | Wave 0 |
| KB-01 | Created entries pass schema validation | unit | `pytest tests/test_lint.py::test_valid_entry_passes -x` | Wave 0 |
| KB-01 | `lint` reports missing required field | unit | `pytest tests/test_lint.py::test_lint_catches_missing_field -x` | Wave 0 |
| KB-01 | `lint` reports empty optional array | unit | `pytest tests/test_lint.py::test_lint_catches_empty_array -x` | Wave 0 |
| KB-01 | `lint` reports slug-filename mismatch | unit | `pytest tests/test_lint.py::test_lint_catches_slug_mismatch -x` | Wave 0 |

### Integration Test Strategy (Real File I/O + Real API)

Per project philosophy (`CLAUDE.md`): "pytest + servicios reales — nunca mocks". All integration tests use real Groq API calls and real file I/O.

Implications:
- Integration tests require `GROQ_API_KEY` in env — skip with `pytest.mark.skipif` if not set
- Integration tests are slow (LLM latency) — mark with `@pytest.mark.integration` and run separately from unit tests
- Unit tests (lint validation) use fixture KB entries — no LLM call needed

### Sampling Rate

- **Per task commit:** `python3 -m pytest tests/test_lint.py -x -q` (unit only, < 5 seconds)
- **Per wave merge:** `python3 -m pytest tests/ -x -q` (all including integration)
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/__init__.py` — make tests a package
- [ ] `tests/conftest.py` — shared fixtures: `tmp_kb_dir`, `sample_note_path`, `sample_kb_entry`
- [ ] `tests/test_lint.py` — covers KB-01 lint validation (unit, no LLM)
- [ ] `tests/test_ingest.py` — covers KB-07 idempotency and CLI flags (integration)
- [ ] `tests/test_contradiction.py` — covers KB-04 contradiction detection (integration)
- [ ] `pytest.ini` — marks for `integration`, default test discovery

---

## Sources

### Primary (HIGH confidence)
- python-frontmatter v1.1.0 — confirmed installed; docs at https://github.com/eyeseast/python-frontmatter
- Groq Python SDK v1.1.2 — confirmed installed; `GROQ_API_KEY` confirmed in env
- `schema.md` — output contract, directly inspected
- `kb/personal/escoliosis-lumbar-diagnostico.md` — confirmed working example entry
- All 14 upstream notes — directly inspected; format confirmed uniform

### Secondary (MEDIUM confidence)
- `llama-3.3-70b-versatile` JSON mode support — confirmed by Groq model list; JSON mode behavior inferred from Groq docs patterns

### Tertiary (LOW confidence — flag for validation)
- `llama-3.3-70b-versatile` response_format JSON mode parameter exact syntax — verify in Wave 0 with a test call before building full extraction pipeline

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — both libraries confirmed installed, API key confirmed
- Architecture: HIGH — derived directly from schema contract and upstream note format inspection
- LLM call patterns: MEDIUM — JSON mode on llama-3.3-70b is standard Groq usage but not tested in this project yet
- Pitfalls: HIGH — derived from direct inspection of 14 notes + schema rules

**Research date:** 2026-04-10
**Valid until:** 2026-05-10 (stable domain; Groq model availability may change faster)
