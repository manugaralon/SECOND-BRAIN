---
phase: 2
slug: knowledge-processor
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-10
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2 (confirmed installed) |
| **Config file** | none — Wave 0 creates `pytest.ini` |
| **Quick run command** | `python3 -m pytest tests/test_lint.py -x -q` |
| **Full suite command** | `python3 -m pytest tests/ -x -q` |
| **Estimated runtime** | ~5s (unit) / ~60s (full with integration) |

---

## Sampling Rate

- **After every task commit:** Run `python3 -m pytest tests/test_lint.py -x -q`
- **After every plan wave:** Run `python3 -m pytest tests/ -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds (unit), 60 seconds (integration)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 02-01-01 | 01 | 0 | KB-01 | unit stub | `pytest tests/test_lint.py -x -q` | ❌ W0 | ⬜ pending |
| 02-01-02 | 01 | 0 | KB-07 | integration stub | `pytest tests/test_ingest.py -x -q` | ❌ W0 | ⬜ pending |
| 02-01-03 | 01 | 0 | KB-04 | integration stub | `pytest tests/test_contradiction.py -x -q` | ❌ W0 | ⬜ pending |
| 02-02-01 | 02 | 1 | KB-01 | unit | `pytest tests/test_lint.py -x -q` | ✅ W0 | ⬜ pending |
| 02-02-02 | 02 | 1 | KB-07 | integration | `pytest tests/test_ingest.py::test_single_note_creates_entries -x` | ✅ W0 | ⬜ pending |
| 02-02-03 | 02 | 1 | KB-07 | integration | `pytest tests/test_ingest.py::test_idempotency -x` | ✅ W0 | ⬜ pending |
| 02-02-04 | 02 | 1 | KB-07 | integration | `pytest tests/test_ingest.py::test_no_confirm_flag -x` | ✅ W0 | ⬜ pending |
| 02-03-01 | 03 | 2 | KB-04 | integration | `pytest tests/test_contradiction.py::test_contradiction_detected -x` | ✅ W0 | ⬜ pending |
| 02-03-02 | 03 | 2 | KB-04 | integration | `pytest tests/test_contradiction.py::test_contradiction_logged -x` | ✅ W0 | ⬜ pending |
| 02-04-01 | 02 | 1 | KB-07 | integration (slow) | `pytest tests/test_ingest.py::test_batch_all_notes -x -m integration` | ✅ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/__init__.py` — make tests a package
- [ ] `tests/conftest.py` — shared fixtures: `tmp_kb_dir`, `sample_note_path`, `sample_kb_entry`
- [ ] `tests/test_lint.py` — unit tests for KB-01 lint validation (no LLM)
- [ ] `tests/test_ingest.py` — integration tests for KB-07 idempotency and CLI flags (real Groq API)
- [ ] `tests/test_contradiction.py` — integration tests for KB-04 contradiction detection (real Groq API)
- [ ] `pytest.ini` — marks for `integration`, default test discovery

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Interactive confirm pause on low-confidence extraction | KB-07 | Requires stdin interaction — pytest can't drive interactive prompts cleanly | Run `python process.py ingest <note>` with a vague note; verify pause appears with write/skip/rename prompt |
| CTA slide ignored in carousel notes | KB-01 | No automated assertion on "ignored" content | Inspect output entries from a carousel note; confirm no entry with concept containing "follow", "like", "subscribe" |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
