---
phase: 03-oracle-interface
plan: "02"
subsystem: oracle
tags: [claude-md, prompt-engineering, knowledge-base, gap-detection, contradiction-surfacing]

# Dependency graph
requires:
  - phase: 03-01
    provides: INDEX.md populated with all 52 KB entries, enabling domain-filter query protocol

provides:
  - CLAUDE.md oracle contract at project root: zero-setup personalized KB interface
  - tests/test_claude_md.py: 6 structural validation tests for oracle contract integrity

affects:
  - All future Claude Code sessions in this project (CLAUDE.md is read at session start)
  - Phase 4 (ChromaDB): oracle contract defines the query interface contract to maintain

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "CLAUDE.md as operative contract: imperative language, concrete thresholds, full KB paths — not suggestions"
    - "Response structure mandate: coverage + personal context + body + contradictions + gaps in fixed order"
    - "Gap detection threshold hard-coded in prompt (<=3 entries = sparse) to prevent session-to-session inconsistency"
    - "Contradiction false-positive handling: evaluate detail field before surfacing conflict"

key-files:
  created:
    - CLAUDE.md
    - tests/test_claude_md.py
  modified: []

key-decisions:
  - "CLAUDE.md uses full paths (kb/concepts/, kb/personal/, kb/INDEX.md) not relative — session-agnostic"
  - "KB Layout section uses indented code block (4 spaces) not fenced block to avoid nested triple-backtick conflicts"
  - "Contradiction Rule includes false-positive handling: check detail field for 'no direct logical conflicts' before surfacing"
  - "Auto-advance applied to checkpoint:human-verify (Task 3) per auto_advance=true config"

patterns-established:
  - "Oracle contract pattern: CLAUDE.md as self-contained instruction set with mandatory sections in fixed order"
  - "Structural test pattern: pytest reads CLAUDE.md as plain text, asserts section headers and required phrases exist"

requirements-completed: [KB-05, KB-06]

# Metrics
duration: 2min
completed: 2026-04-13
---

# Phase 3 Plan 02: Oracle Interface Contract Summary

**CLAUDE.md oracle contract with gap detection (<=3 entries = "cobertura escasa"), mandatory personal context loading, and contradiction surfacing — backed by 6 structural pytest tests**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-04-13T07:14:24Z
- **Completed:** 2026-04-13T07:16:08Z
- **Tasks:** 2 automated + 1 auto-approved checkpoint
- **Files modified:** 2

## Accomplishments
- CLAUDE.md oracle contract at project root: 6 sections (KB Layout, Session Initialization, Query Protocol, Gap Detection, Contradiction Rule, Response Structure)
- Zero-setup personal context loading: session starts with mandatory read of all 4 kb/personal/ entries
- Gap detection with hard-coded threshold: <=3 entries triggers "cobertura escasa" warning unprompted
- Contradiction surfacing with false-positive filter: evaluates `detail` field before reporting conflict
- 6 pytest structural tests covering existence, sections, paths, domains, gap phrase, and imperative language count

## Task Commits

Each task was committed atomically:

1. **Task 1: Write CLAUDE.md oracle contract** - `40e78f1` (feat)
2. **Task 2: Add test_claude_md.py structural validation** - `08a401b` (feat) — includes CLAUDE.md path fix
3. **Task 3: Verify oracle in fresh session** - checkpoint:human-verify, auto-approved (auto_advance=true)

## Files Created/Modified
- `CLAUDE.md` — Oracle contract: session initialization, query protocol, gap detection, contradiction rule, response structure template
- `tests/test_claude_md.py` — 6 structural validation tests (unit, no LLM)

## Decisions Made
- CLAUDE.md uses full paths (kb/concepts/, kb/personal/, kb/INDEX.md) not relative — ensures fresh-session portability
- KB Layout uses indented code block (4 spaces) not fenced block to avoid nested triple-backtick parsing issues
- Contradiction false-positive handling explicit: if `detail` says "no direct logical conflicts", skip and do not report
- Auto-advance applied to Task 3 checkpoint (auto_advance=true in config) — human verify deferred

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed kb/concepts/ path missing from CLAUDE.md KB Layout section**
- **Found during:** Task 2 (test_claude_md_kb_paths test failure)
- **Issue:** KB Layout block used short paths (`concepts/`) without `kb/` prefix; test requires `kb/concepts/`
- **Fix:** Changed indented block to use full paths `kb/concepts/`, `kb/personal/`, `kb/INDEX.md`
- **Files modified:** CLAUDE.md
- **Verification:** `python3 -m pytest tests/test_claude_md.py -x -q` — 6 passed
- **Committed in:** 08a401b (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 — bug: missing path prefix)
**Impact on plan:** Necessary for test correctness. Path fix also improves CLAUDE.md clarity — full paths are unambiguous in fresh sessions.

## Issues Encountered
- Pre-existing integration test `test_contradiction_logged` fails due to Groq API returning malformed JSON (intermittent). Out of scope — not caused by this plan's changes. All 18 non-integration tests pass.

## User Setup Required
None — no external service configuration required.

## Next Phase Readiness
- Oracle contract is deployed. Fresh Claude Code sessions now have full KB navigation instructions.
- Phase 3 complete: INDEX.md populated (Plan 01) + CLAUDE.md oracle contract (Plan 02).
- Phase 4 (ChromaDB semantic search) deferred until corpus exceeds ~100 entries.
- Human verification of oracle behavior in live session recommended before Phase 4.

---
*Phase: 03-oracle-interface*
*Completed: 2026-04-13*
