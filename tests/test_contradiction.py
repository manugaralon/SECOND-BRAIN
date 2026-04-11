"""KB-04: contradiction detection integration tests (real Groq API)."""
import json
import os
import shutil
from pathlib import Path

import frontmatter
import pytest

pytestmark = pytest.mark.integration

skip_no_groq = pytest.mark.skipif(
    not os.environ.get("GROQ_API_KEY"),
    reason="GROQ_API_KEY not set in environment",
)

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _write_existing_entry(kb_dir: Path, slug: str, summary: str, domain: str = "ia") -> Path:
    post = frontmatter.Post("body")
    post["concept"] = slug
    post["domain"] = domain
    post["confidence"] = 0.85
    post["summary"] = summary
    post["sources"] = [{"note": "seed", "date": "2026-04-10"}]
    post["last_updated"] = "2026-04-10"
    path = kb_dir / f"{slug}.md"
    path.write_text(frontmatter.dumps(post))
    return path


@skip_no_groq
def test_contradiction_detected(tmp_kb_dir: Path):
    """When a new entry directly contradicts an existing same-domain entry, find_contradictions returns a non-empty list."""
    from process import find_contradictions

    kb_concepts = tmp_kb_dir / "concepts"
    _write_existing_entry(
        kb_concepts,
        slug="few-shot-best",
        summary="Few-shot prompting always outperforms zero-shot prompting on reasoning tasks",
    )

    new_entry = {
        "concept": "zero-shot-best",
        "domain": "ia",
        "summary": "Zero-shot prompting outperforms few-shot prompting on reasoning tasks because examples bias the model",
    }

    contradictions = find_contradictions(new_entry, kb_concepts)
    assert isinstance(contradictions, list)
    assert len(contradictions) >= 1, "Expected at least one contradiction with few-shot-best"
    assert any(c["concept"] == "few-shot-best" for c in contradictions)


@skip_no_groq
def test_contradiction_logged(tmp_kb_dir: Path, tmp_path: Path):
    """When a contradiction is detected during ingest, processed.log records it."""
    from process import ingest_note

    kb_concepts = tmp_kb_dir / "concepts"
    _write_existing_entry(
        kb_concepts,
        slug="few-shot-best",
        summary="Few-shot prompting always outperforms zero-shot prompting on reasoning tasks",
    )

    # Hand-craft a tiny note that asserts the opposite
    note_path = tmp_path / "contradict_note.md"
    note_path.write_text(
        "---\n"
        "title: Test\n"
        "url: http://example.com\n"
        "topic: claude-env\n"
        "type: video\n"
        "author: tester\n"
        "processed_date: 2026-04-10\n"
        "tags: [test]\n"
        "---\n\n"
        "## Transcripcion\n\n"
        "Zero-shot prompting outperforms few-shot prompting on reasoning tasks. "
        "Examples bias the model and reduce accuracy. This contradicts the few-shot-best position.\n"
    )

    log_path = tmp_path / "processed.log"
    ingest_note(
        note_path=note_path,
        kb_dir=kb_concepts,
        log_path=log_path,
        no_confirm=True,
    )

    # processed.log must contain a record mentioning contradictions
    log_lines = [json.loads(line) for line in log_path.read_text().splitlines() if line.strip()]
    assert any(
        rec.get("contradictions_found", 0) >= 1 or rec.get("status") == "contradictions"
        for rec in log_lines
    ), f"No contradiction record in log: {log_lines}"
