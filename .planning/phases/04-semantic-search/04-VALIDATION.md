---
phase: 4
slug: semantic-search
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-13
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | none — existing pytest setup |
| **Quick run command** | `python3 -m pytest tests/test_vector_index.py -q` |
| **Full suite command** | `python3 -m pytest tests/ -q` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python3 -m pytest tests/test_vector_index.py -q`
- **After every plan wave:** Run `python3 -m pytest tests/ -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 4-01-01 | 01 | 1 | chromadb install | integration | `python3 -c "import chromadb; print('ok')"` | ❌ W0 | ⬜ pending |
| 4-01-02 | 01 | 1 | collection populated | integration | `pytest tests/test_vector_index.py::test_collection_populated -q` | ❌ W0 | ⬜ pending |
| 4-01-03 | 01 | 1 | sync on ingest | integration | `pytest tests/test_vector_index.py::test_sync_on_ingest -q` | ❌ W0 | ⬜ pending |
| 4-02-01 | 02 | 2 | query returns slugs | integration | `pytest tests/test_vector_index.py::test_query_returns_slugs -q` | ❌ W0 | ⬜ pending |
| 4-02-02 | 02 | 2 | oracle reads via slugs | integration | `pytest tests/test_vector_index.py::test_oracle_slug_resolution -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_vector_index.py` — stubs for all 5 test cases above
- [ ] `chromadb` and `sentence-transformers` installed in environment

*Existing pytest infrastructure covers the framework — only new test file needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Multilingual query relevance | Success criteria 2 | Semantic quality can't be asserted with `==` | Query "ejercicios para la espalda", verify escoliosis-related concepts rank in top 3 |
| No KB file mutation | Success criteria 3 | File-not-modified assertion not meaningful in test | `git diff kb/` shows no changes after `rebuild-vector-index` |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
