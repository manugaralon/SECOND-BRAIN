---
phase: 02-knowledge-processor
plan: "02"
subsystem: knowledge-processor
tags: [python, groq, llm-extraction, lint, cli, tdd, idempotency]

requires:
  - 02-01 (pytest infrastructure + TDD Wave 0 stubs)
provides:
  - process.py CLI with lint and ingest subcommands
  - Groq LLM extraction pipeline (Pass 1 only)
  - Idempotency via processed.log JSONL
  - Schema validation via lint_entry / lint_all
affects: [02-03-PLAN]

tech-stack:
  added: [groq, python-frontmatter]
  patterns:
    - "Single-file CLI: argparse subparsers for lint and ingest"
    - "TDD Green: Wave 0 stubs from Plan 01 turn green as code lands"
    - "Idempotency log: JSONL written AFTER all KB entries committed to disk"
    - "Groq response_format json_object for deterministic structured extraction"
    - "Lazy import of Groq inside extract_concepts — avoids ImportError when GROQ_API_KEY absent at module level"

key-files:
  created:
    - process.py
  modified: []

key-decisions:
  - "Groq imported lazily inside extract_concepts() — module-level import would fail in test_lint.py (unit tests) when GROQ_API_KEY absent; lazy import lets unit tests run cleanly"
  - "process.py implements both Task 1 and Task 2 in a single commit because the full ingest pipeline was specified in the plan body, not incrementally; no partial-run state to track"
  - "Low-confidence concepts skipped (not rejected) in --no-confirm mode; written to processed.log with entries_skipped counter for traceability"
  - "Domain coercion fallback: if LLM returns invalid/missing domain, TOPIC_TO_DOMAIN mapping applied, then default 'ia'"

metrics:
  duration: "3min (169s)"
  completed: "2026-04-11"
  tasks: 2
  files_modified: 1
---

# Phase 2 Plan 02: process.py CLI — lint + Groq ingest pipeline Summary

**418-line single-file CLI with `lint` and `ingest` subcommands: schema validation, Groq LLM extraction with json_object mode, idempotency via JSONL log, and interactive low-confidence prompt**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-04-11T20:33:13Z
- **Completed:** 2026-04-11T20:36:~02Z
- **Tasks:** 2 (implemented together as plan specified full process.py)
- **Files modified:** 1

## Accomplishments

- `process.py` created at project root — 418 lines, single file, no external schema validators
- `lint_entry` validates: required fields, domain enum, confidence range, sources structure, last_updated format, slug-filename match, empty optional arrays (7 distinct rules)
- `lint_all` scans a directory and returns path→errors dict
- CLI `lint` subcommand covers `kb/concepts/` and `kb/personal/` by default; `--kb-dir` overrides; exits 0/1
- `extract_concepts` calls Groq `llama-3.3-70b-versatile` with `response_format={"type": "json_object"}` at temperature 0.1
- `write_kb_entry` writes schema-conformant frontmatter via python-frontmatter; omits empty optional arrays
- `ingest_note` end-to-end: idempotency check → LLM extract → interactive confirm / --no-confirm → collision check → write → log
- `processed.log` written AFTER all KB entries flushed to disk (no partial-run corruption)
- All 4 existing `kb/personal/` entries lint clean with zero errors

## Task Commits

1. **Task 1 + Task 2: process.py full implementation** — `5e92e6f` (feat)
   - Schema constants, lint functions, ingest pipeline, interactive prompt, CLI handlers all implemented in one atomic commit because the plan provided the complete process.py specification upfront

## Test Status

### Passing

| Test file | Count | Notes |
|-----------|-------|-------|
| tests/test_lint.py | 7/7 | All unit tests green |
| tests/test_ingest.py::test_single_note_creates_entries | 1/1 | Real Groq API — 7 entries from sample_note.md |
| tests/test_ingest.py::test_idempotency | 1/1 | Second run yields [SKIP], no new files |
| tests/test_ingest.py::test_no_confirm_flag | 1/1 | Subprocess exits 0, no stdin block |

### Intentionally still RED (Plan 03's scope)

| Test | Reason |
|------|--------|
| tests/test_ingest.py::test_batch_all_notes | `@pytest.mark.slow` — requires all 14 notes + Groq; Plan 03 closes this |
| tests/test_contradiction.py::* | Contradiction detection not implemented — Plan 03 adds `find_contradictions` |

## Verification Run

```
python3 process.py lint
→ [INFO] kb/concepts: 0 entries scanned
→ [INFO] kb/personal: 4 entries scanned
→ [OK] no violations

python3 process.py lint --kb-dir tests/fixtures
→ exits 1, 9 violations (3 fixture errors + 6 from sample_note.md treated as KB entry)
→ contains: "confidence", "gaps", "slug"

python3 process.py ingest tests/fixtures/sample_note.md --no-confirm --kb-dir /tmp/test-kb --log /tmp/test-processed.log
→ [WRITE] kernel-prompt-engineering-framework (confidence=0.90)
→ [WRITE] importance-of-simplicity-in-prompts (confidence=0.80)
→ [WRITE] verifiability-in-prompts (confidence=0.80)
→ [WRITE] reproducibility-in-prompts (confidence=0.80)
→ [WRITE] narrow-scope-in-prompts (confidence=0.80)
→ [WRITE] explicit-constraints-in-prompts (confidence=0.80)
→ [WRITE] logical-structure-in-prompts (confidence=0.80)
→ [DONE] created=7 skipped=0
→ exits 0

# Re-run (idempotency):
→ [SKIP] sample_note already processed
→ [DONE] created=0 skipped=0
→ 7 files unchanged
```

## Extraction Prompt Notes

The KERNEL framework note (6 images, `claude-env` topic, `ia` domain) yielded 7 concepts — all at confidence ≥ 0.80. The last CTA slide (image 6) was correctly ignored. No low-confidence extractions occurred for this note, so the interactive flow was not exercised in this run; `--no-confirm` path is confirmed green via test_no_confirm_flag.

`TOPIC_TO_DOMAIN = {"claude-env": "ia"}` mapping worked correctly — all 7 concepts received domain `ia` without needing LLM domain assignment.

## process.py Structure

| Section | Lines | Purpose |
|---------|-------|---------|
| Constants | 1-55 | REQUIRED_FIELDS, VALID_DOMAINS, paths, thresholds, Groq model, extraction prompt |
| Lint | 57-122 | lint_entry, lint_all |
| Ingest helpers | 124-210 | load_note, load_processed_slugs, append_processed, extract_concepts, write_kb_entry, _interactive_confirm |
| ingest_note | 212-258 | End-to-end note processing |
| CLI handlers | 260-330 | _cmd_lint, _cmd_ingest |
| main() | 332-370 | argparse with ingest + lint subparsers |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Lazy import for Groq to avoid ImportError in unit tests**
- **Found during:** Task 1 implementation
- **Issue:** Plan's code skeleton placed `from groq import Groq` at the top level. This would cause `ImportError` when `groq` package is installed but `GROQ_API_KEY` is absent — or worse, during test_lint.py collection which never uses Groq.
- **Fix:** Moved `from groq import Groq` inside `extract_concepts()` body. Module loads cleanly; Groq only imported when actually called.
- **Files modified:** process.py
- **Commit:** 5e92e6f

None others — plan executed as specified.

## Self-Check: PASSED

- process.py: FOUND at project root (418 lines)
- Commit 5e92e6f: FOUND in git log
- test_lint.py: 7/7 passing
- test_ingest.py (non-batch): 3/3 passing
- kb/personal/ lint: 0 violations
