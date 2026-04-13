---
phase: 03-oracle-interface
plan: 01
subsystem: indexing
tags: [python, frontmatter, index, kb, cli]

requires:
  - phase: 02-knowledge-processor
    provides: kb/concepts/*.md and kb/personal/*.md populated via process.py ingest

provides:
  - rebuild_index() function in process.py regenerating INDEX.md from disk
  - rebuild-index CLI subcommand (no args needed)
  - kb/INDEX.md with all 52 entries (48 concepts + 4 personal), domain-filterable
  - tests/test_index.py with 5 completeness tests

affects:
  - 03-oracle-interface/03-02 (oracle domain-filtering depends on complete INDEX.md)

tech-stack:
  added: []
  patterns:
    - "INDEX.md as machine-readable registry: slug | domain | summary | path columns"
    - "rebuild_index() called automatically at end of ingest — index always in sync"
    - "Test suite validates completeness via filesystem glob vs INDEX.md slug set"

key-files:
  created:
    - kb/INDEX.md
    - tests/test_index.py
  modified:
    - process.py

key-decisions:
  - "INDEX.md separator comment retained from original format — rebuild always overwrites full file, not just entries below separator"
  - "Personal entries sorted alphabetically first, concepts alphabetical after — consistent ordering for git diffs"
  - "Pipe characters in summaries escaped to \\| to avoid breaking Markdown table"
  - "ingest auto-calls rebuild_index() so index never drifts after a write"

patterns-established:
  - "Index completeness tested via set difference: filesystem_slugs - index_slugs = missing"
  - "Orphan check (index_slugs - filesystem_slugs) prevents stale entries after manual KB pruning"

requirements-completed: [KB-05]

duration: 10min
completed: 2026-04-13
---

# Phase 03 Plan 01: Index Backfill Summary

**rebuild_index() in process.py regenerates kb/INDEX.md from disk — 52 entries (48 concepts + 4 personal), with 5-test completeness suite and auto-sync on ingest**

## Performance

- **Duration:** ~10 min
- **Started:** 2026-04-13T00:00:00Z
- **Completed:** 2026-04-13T00:10:00Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Added `rebuild_index()` function scanning both KB directories via frontmatter.load()
- Wired `rebuild-index` as a new argparse subcommand alongside `ingest` and `lint`
- INDEX.md now contains all 52 entries in a domain-filterable Markdown table
- Added auto-rebuild call at end of `_cmd_ingest` so future ingests keep the index in sync
- Created `tests/test_index.py` with 5 green tests validating completeness, no orphans, and entry count

## Task Commits

1. **Task 1: Add rebuild-index subcommand and populate INDEX.md** - `5bb0bdd` (feat)
2. **Task 2: Add test_index.py — INDEX.md completeness validation** - `12e58eb` (test)

## Files Created/Modified

- `process.py` - Added INDEX_PATH constant, rebuild_index(), _cmd_rebuild_index(), rebuild-index subparser, auto-rebuild in _cmd_ingest
- `kb/INDEX.md` - Rebuilt from disk: 4 personal + 48 concept entries in Markdown table
- `tests/test_index.py` - 5 completeness tests (file_exists, all_concepts, all_personal, no_orphans, entry_count)

## Decisions Made

- Pipe characters in summaries are escaped (`\|`) to prevent Markdown table corruption
- Personal entries listed before concepts in INDEX.md for consistent ordering
- `rebuild_index()` overwrites the full INDEX.md file (not just below the separator comment) — simpler and safer than partial updates

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- `test_contradiction_detected` in `tests/test_contradiction.py` fails due to Groq API network unavailability in sandbox (pre-existing, unrelated to this plan). Documented in deferred-items.

## Next Phase Readiness

- INDEX.md is complete and machine-readable — oracle (Plan 02) can immediately filter by domain column
- test_index.py ensures INDEX.md stays complete as corpus grows
- No blockers for 03-02

---
*Phase: 03-oracle-interface*
*Completed: 2026-04-13*
