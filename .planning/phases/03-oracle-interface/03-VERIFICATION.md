---
phase: 03-oracle-interface
verified: 2026-04-13T09:00:00Z
status: human_needed
score: 5/6 must-haves verified (automated); 1/6 requires live-session test
re_verification: false
human_verification:
  - test: "Open a NEW Claude Code session in SECONDBRAIN directory and ask: 'que ejercicios puedo hacer para la escoliosis'"
    expected: "Response contains [Dominios consultados: ...] with entry counts, [Contexto personal aplicado: ...] mentioning escoliosis AND pies-planos, personalized answer, and 'cobertura escasa' if domain has <= 3 entries"
    why_human: "CLAUDE.md instructs Claude Code at session start. The oracle protocol (load personal, filter by domain, surface contradictions, report gaps) can only be verified by running an actual Claude Code session — no programmatic substitute."
  - test: "In the same session ask: 'que sabes sobre psicologia'"
    expected: "Response includes 'cobertura escasa' and the numeric count for the psicologia domain"
    why_human: "Gap detection trigger (<=3 entries) requires counting loaded domain entries at query time — cannot be verified without a live model session."
  - test: "In the same session ask about a topic with a contradicts field (e.g., 'que es claude code como shell')"
    expected: "Oracle surfaces the contradiction or correctly identifies it as a false positive by checking the detail field. Never silently resolves it."
    why_human: "Contradiction surfacing requires the model to read frontmatter fields and reason about them — cannot be unit-tested."
---

# Phase 03: Oracle Interface Verification Report

**Phase Goal:** Turn the populated KB into a queryable oracle — so Claude Code (in a fresh session) can answer personal knowledge questions by reading from the KB on demand.
**Verified:** 2026-04-13T09:00:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | INDEX.md contains a row for every .md file in kb/concepts/ and kb/personal/ | VERIFIED | test_index_contains_all_concepts + test_index_contains_all_personal both pass; INDEX.md has 209 entries (205 concepts + 4 personal) matching exact filesystem count |
| 2 | process.py has a rebuild-index subcommand that regenerates INDEX.md from disk | VERIFIED | `def rebuild_index` at line 122, `_cmd_rebuild_index` at line 609, subparser wired at line 637, `process.py rebuild-index` exits 0 |
| 3 | test_index.py validates INDEX.md completeness against filesystem | VERIFIED | 5 tests present (file_exists, all_concepts, all_personal, no_orphans, entry_count), all 5 pass |
| 4 | A fresh Claude Code session can answer personalized questions referencing personal context without manual setup | HUMAN NEEDED | CLAUDE.md exists with mandatory Session Initialization section; behavioral outcome requires live session |
| 5 | The oracle reports domain entry counts and flags sparse domains (<=3 entries) unprompted | HUMAN NEEDED | Gap Detection section present in CLAUDE.md with "cobertura escasa" threshold; behavioral compliance requires live session |
| 6 | Every substantive answer declares which domains were consulted | HUMAN NEEDED | Response Structure section mandates coverage line; compliance requires live session |

**Score (automated):** 3/3 Plan-01 truths VERIFIED, 0/3 Plan-02 behavioral truths verified (require human), 2 structural truths for Plan-02 fully verified

---

## Required Artifacts

### Plan 01 Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `kb/INDEX.md` | Complete domain-filterable index of all KB entries | VERIFIED | 209 entries (205 concepts + 4 personal); header "# Knowledge Base Index"; separator comment present; contains claude-code-functionality, escoliosis-lumbar-diagnostico, model-swapping-in-claude-code |
| `tests/test_index.py` | Automated validation that INDEX.md covers all KB files | VERIFIED | Contains test_index_contains_all_concepts, test_index_contains_all_personal, test_index_has_no_orphans, test_index_entry_count; all 5 tests pass |
| `process.py` (rebuild-index) | rebuild-index subcommand regenerates INDEX.md from disk | VERIFIED | def rebuild_index() at line 122; argparse subcommand at line 637; auto-called from ingest at line 604 |

### Plan 02 Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `CLAUDE.md` | Oracle contract — all 6 required sections, imperative language, KB path references, all 8 domains | VERIFIED | All 6 sections present (KB Layout, Session Initialization, Query Protocol, Gap Detection, Contradiction Rule, Response Structure); kb/personal/, kb/concepts/, kb/INDEX.md all referenced; all 8 domains listed; imperative language count passes threshold |
| `tests/test_claude_md.py` | Structural validation of CLAUDE.md oracle contract | VERIFIED | 6 tests: exists, sections, kb_paths, domains, gap_threshold, imperative_language; all 6 pass |

---

## Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| process.py rebuild-index | kb/INDEX.md | reads frontmatter from kb/concepts/*.md and kb/personal/*.md, writes markdown table | WIRED | rebuild_index() at line 122 wired to _cmd_rebuild_index at line 609, argparse registered at line 637; auto-called from ingest at line 604 |
| CLAUDE.md | kb/INDEX.md | Query Protocol instructs Claude to read INDEX.md for domain filtering | WIRED | "Open `kb/INDEX.md`" in Query Protocol step 2; also referenced in KB Layout section |
| CLAUDE.md | kb/personal/*.md | Session Initialization mandates loading all personal context files | WIRED | "Read every file in `kb/personal/`" in Session Initialization section |
| CLAUDE.md | kb/concepts/*.md | Query Protocol reads concept files matched by domain from INDEX.md | WIRED | "Read each concept file listed in INDEX.md for those domains" in Query Protocol step 3; kb/concepts/ present in KB Layout |

---

## Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| KB-05 | 03-01, 03-02 | El sistema detecta gaps: "sobre X hay poco conocimiento acumulado" | VERIFIED (structural) | Gap Detection section in CLAUDE.md with "cobertura escasa" phrase and <=3 threshold; test_claude_md_gap_threshold passes; behavioral verification requires human |
| KB-06 | 03-02 | Claude Code puede consultar la KB y responder preguntas sintetizadas y personalizadas | VERIFIED (structural) | CLAUDE.md oracle contract with full Query Protocol, Session Initialization, and Response Structure; test_claude_md_sections passes; behavioral verification requires human |

No orphaned requirements — both KB-05 and KB-06 are claimed by plans and verified against REQUIREMENTS.md. REQUIREMENTS.md traceability table marks both as Complete.

---

## Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| None | — | No TODOs, FIXMEs, placeholder returns, or stub implementations found in any phase-03 artifact | — | — |

---

## Test Suite Status

| Suite | Tests | Result | Notes |
|-------|-------|--------|-------|
| tests/test_index.py | 5 | 5 passed | All completeness checks green |
| tests/test_claude_md.py | 6 | 6 passed | All structural checks green |
| tests/test_lint.py | 7 | 7 passed | Pre-existing; unaffected |
| tests/test_contradiction.py | 1 | 1 FAILED | Pre-existing Groq API network failure in sandbox — not caused by Phase 03, documented in both summaries |

Non-API test total: 18/18 passed.

---

## Human Verification Required

### 1. Oracle personal context loading and domain reporting

**Test:** Open a NEW Claude Code session (fresh context, no history) in the SECONDBRAIN project directory. Ask: "que ejercicios puedo hacer para la escoliosis"

**Expected:**
- Response contains `[Dominios consultados: fisioterapia (N entradas)]` or similar coverage line
- Response contains `[Contexto personal aplicado: ...]` mentioning escoliosis AND pies-planos (cross-apply requirement)
- Answer is personalized to Manuel's specific conditions, not generic advice
- If fisioterapia has <=3 entries: "cobertura escasa" appears before the main answer

**Why human:** CLAUDE.md is an instruction set for the Claude model at session start. The Session Initialization and Query Protocol only execute inside a real Claude Code session — no programmatic test can confirm the model reads and follows them.

### 2. Gap detection threshold

**Test:** In the same session ask: "que sabes sobre psicologia"

**Expected:** Response includes "sobre psicologia hay [N] entradas — cobertura escasa" (since psicologia likely has <=3 entries)

**Why human:** Entry counting and threshold comparison happen at query time inside the model session.

### 3. Contradiction surfacing

**Test:** In the same session ask: "que es claude code como shell" (or another topic where the contradicts field is present)

**Expected:** Oracle either surfaces both conflicting positions explicitly ("Estas dos entradas se contradicen: ...") or correctly identifies the contradiction as a false positive by checking the `detail` field — it must never silently resolve it.

**Why human:** Requires the model to read frontmatter fields and apply conditional reasoning. Cannot be unit-tested.

---

## Observations

**INDEX.md entry count:** The plan was written when the KB had 52 entries. At verification time the KB has 209 entries (205 concepts + 4 personal). The rebuild-index subcommand and tests use `>= 52` as the threshold — both correctly track the actual corpus size. This is not a gap; it confirms the indexing mechanism scales as designed.

**Task 3 auto-approve:** Plan 02 Task 3 (human-verify checkpoint) was auto-approved per `auto_advance=true` in config. The oracle behavioral verification is therefore pending human confirmation, as expected and documented in the SUMMARY.

---

_Verified: 2026-04-13T09:00:00Z_
_Verifier: Claude (gsd-verifier)_
