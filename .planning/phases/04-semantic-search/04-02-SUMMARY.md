---
phase: 04-semantic-search
plan: "02"
subsystem: vector-search
tags: [chromadb, sentence-transformers, semantic-search, oracle, CLAUDE.md]

requires:
  - phase: 04-semantic-search/04-01
    provides: _get_vector_collection, rebuild_vector_index, _sync_to_vector_index, CHROMA_PATH constants

provides:
  - query_vector_index() function with n_results clamp (Pitfall 3 safe)
  - python3 process.py query CLI subcommand with --domain, --n-results, --chroma-path
  - CLAUDE.md Query Protocol with vector-or-full-read switch at >20 entries threshold

affects: [oracle-session, fisioterapia-queries, large-domain-retrieval]

tech-stack:
  added: []
  patterns:
    - "n_results clamped to col.count() before col.query() to prevent ChromaDB crash on small collections"
    - "domain filter via where= kwarg: single domain uses dict, multiple uses $in operator, no filter when domains=None"
    - "CLAUDE.md oracle protocol uses per-domain entry count to route between vector path and full-read path"

key-files:
  created: []
  modified:
    - process.py
    - CLAUDE.md

key-decisions:
  - "query_vector_index omits where= entirely when domains is None/empty — no domain: null filter that would break ChromaDB"
  - "CLAUDE.md threshold set at >20 entries — below this, full-read is fast enough; above, vector narrowing reduces context load"
  - "CLI _cmd_query distinguishes empty-collection (prints [INFO] rebuild hint) from zero-matches (prints [INFO] no matches)"

patterns-established:
  - "Vector path is internal optimization only — user-facing response structure unchanged"
  - "Personal context (kb/personal/) always full-read at session start, never via vector path"

requirements-completed: [SC-2]

duration: 3min
completed: "2026-04-14"
---

# Phase 4 Plan 02: Semantic Search Query Path Summary

**`query_vector_index()` with Pitfall-3-safe n_results clamp, `query` CLI subcommand, and CLAUDE.md oracle protocol updated to route large domains (>20 entries) through vector retrieval**

## Performance

- **Duration:** 3 min
- **Started:** 2026-04-14T13:09:46Z
- **Completed:** 2026-04-14T13:12:58Z
- **Tasks:** 2 of 3 (Task 3 is a human checkpoint — pending)
- **Files modified:** 2

## Accomplishments

- `query_vector_index()` added to process.py: returns ranked slugs with domain filter, safe on empty/small collections (n_results clamped to col.count())
- `python3 process.py query "<text>" --domain D --n-results N` CLI subcommand works end-to-end
- CLAUDE.md Query Protocol steps 2-3 replaced with conditional: vector path for >20 entries, full-read fallback for smaller domains
- Process Commands section extended with rebuild-vector-index and query subcommands
- tests/test_vector_index.py::test_query_returns_slugs and ::test_oracle_slug_resolution both pass

## Task Commits

1. **Task 1: Add query_vector_index() + query CLI subcommand** - `e296107` (feat)
2. **Task 2: Update CLAUDE.md oracle Query Protocol** - `e88498e` (feat)

## Files Created/Modified

- `process.py` — query_vector_index() function + _cmd_query handler + query subparser in main()
- `CLAUDE.md` — Query Protocol steps 2-3 updated, Process Commands extended

## Decisions Made

- `query_vector_index` omits `where=` entirely when `domains` is None/empty — passing `{"domain": None}` would break ChromaDB
- CLI distinguishes empty-collection from zero-matches with different [INFO] messages
- CLAUDE.md threshold at >20 entries balances retrieval quality vs. full-read cost

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- `python3 process.py query --help` did not contain "Semantic query" by default (argparse shows parser help= only in parent --help). Fixed by adding `description=` to the subparser alongside `help=`. This is a minor deviation from plan wording but satisfies the acceptance criteria intent.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Task 3 (checkpoint:human-verify) is pending: oracle must be tested in a fresh session to confirm it uses the vector path on fisioterapia (>20 entries) and returns a coherent personalized answer
- After checkpoint approval, SC-2 is verified end-to-end
- Phase 04 complete once checkpoint is approved

---
*Phase: 04-semantic-search*
*Completed: 2026-04-14*
