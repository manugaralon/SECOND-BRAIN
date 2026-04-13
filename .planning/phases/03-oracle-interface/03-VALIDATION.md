---
phase: 3
slug: oracle-interface
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-13
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (existing) |
| **Config file** | pytest.ini |
| **Quick run command** | `python3 -m pytest tests/ -x -q` |
| **Full suite command** | `python3 -m pytest tests/ -q` |
| **Estimated runtime** | ~5 seconds (non-API tests) |

---

## Sampling Rate

- **After every task commit:** Run `python3 -m pytest tests/test_lint.py -x -q`
- **After every plan wave:** Run `python3 -m pytest tests/ -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 3-01-01 | 01 | 1 | KB-05 | lint | `python3 process.py lint` exits 0 | ✅ | ⬜ pending |
| 3-01-02 | 01 | 1 | KB-05 | file | `test -f kb/INDEX.md && grep -c slug kb/INDEX.md \| awk '$1>=52'` | ✅ | ⬜ pending |
| 3-02-01 | 02 | 2 | KB-06 | file | `test -f CLAUDE.md && grep -c "oracle" CLAUDE.md` | ✅ | ⬜ pending |
| 3-02-02 | 02 | 2 | KB-06 | manual | Fresh session oracle response check | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- No new test stubs required — oracle is CLAUDE.md prompt engineering
- Existing `tests/test_lint.py` covers KB schema validation
- INDEX.md backfill verified via `grep -c slug kb/INDEX.md` (must show ≥52 entries)

*Existing infrastructure covers all automated phase requirements.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Oracle references personal context (escoliosis) in answer | KB-06 | Requires live Claude Code session with fresh context | Open fresh session, type "qué ejercicios puedo hacer para la escoliosis", verify response cites personal entries |
| Oracle reports "cobertura escasa" for low-coverage domains | KB-06 | Requires interactive session judgment | Ask about a domain with ≤3 entries, verify unprompted coverage note |
| Oracle surfaces both sides of a contradiction | KB-06 | Requires live session + contradicting entries | Query topic with `contradicts` field, verify both positions presented |
| Oracle declares domains consulted | KB-06 | Session output validation | Verify every substantive answer lists KB domains read |
| Zero manual setup in fresh session | KB-05, KB-06 | End-to-end session test | Open fresh Claude Code, read only CLAUDE.md, ask KB question |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
