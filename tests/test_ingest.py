"""KB-07: ingest pipeline integration tests (real Groq API + real file I/O)."""
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration

skip_no_groq = pytest.mark.skipif(
    not os.environ.get("GROQ_API_KEY"),
    reason="GROQ_API_KEY not set in environment",
)

PROJECT_ROOT = Path(__file__).parent.parent
REAL_NOTES_DIR = Path("/home/manuel/Desktop/PROJECTS/IMPENV/pipeline/notes")


def _run_process(*args: str, cwd: Path) -> subprocess.CompletedProcess:
    """Invoke `python process.py ...` from a given working directory."""
    return subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "process.py"), *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
    )


@pytest.fixture
def isolated_workspace(tmp_path: Path, sample_note_path: Path) -> Path:
    """A temp dir containing kb/ tree, an empty processed.log, and a notes/ dir with one sample note."""
    ws = tmp_path / "workspace"
    (ws / "kb" / "concepts").mkdir(parents=True)
    (ws / "kb" / "personal").mkdir(parents=True)
    (ws / "notes").mkdir(parents=True)
    shutil.copy(sample_note_path, ws / "notes" / "sample_note.md")
    return ws


@skip_no_groq
def test_single_note_creates_entries(isolated_workspace: Path):
    """ingest <file> on a real carousel note creates >=1 schema-valid kb/concepts/*.md entries."""
    from process import ingest_note
    ingest_note(
        note_path=isolated_workspace / "notes" / "sample_note.md",
        kb_dir=isolated_workspace / "kb" / "concepts",
        log_path=isolated_workspace / "processed.log",
        no_confirm=True,
    )
    created = list((isolated_workspace / "kb" / "concepts").glob("*.md"))
    assert len(created) >= 1, "Expected at least one KB entry to be created"
    # Lint each created entry
    from process import lint_entry
    for entry_path in created:
        errors = lint_entry(entry_path)
        assert errors == [], f"{entry_path.name}: {errors}"


@skip_no_groq
def test_idempotency(isolated_workspace: Path):
    """Running ingest twice on the same note creates no duplicate entries."""
    from process import ingest_note
    kb = isolated_workspace / "kb" / "concepts"
    log = isolated_workspace / "processed.log"
    note = isolated_workspace / "notes" / "sample_note.md"

    ingest_note(note_path=note, kb_dir=kb, log_path=log, no_confirm=True)
    first_run = sorted(p.name for p in kb.glob("*.md"))

    ingest_note(note_path=note, kb_dir=kb, log_path=log, no_confirm=True)
    second_run = sorted(p.name for p in kb.glob("*.md"))

    assert first_run == second_run, "Second run must not create new files"


@skip_no_groq
def test_no_confirm_flag(isolated_workspace: Path):
    """--no-confirm must complete without blocking on stdin even when low-confidence concepts are extracted."""
    result = _run_process(
        "ingest",
        str(isolated_workspace / "notes" / "sample_note.md"),
        "--no-confirm",
        cwd=isolated_workspace,
    )
    assert result.returncode == 0, f"stdout={result.stdout}\nstderr={result.stderr}"


@skip_no_groq
@pytest.mark.slow
def test_batch_all_notes(tmp_path: Path):
    """ingest --all processes every note in NOTES_DIR and produces >=14 entries total."""
    ws = tmp_path / "ws"
    (ws / "kb" / "concepts").mkdir(parents=True)
    (ws / "notes").mkdir(parents=True)
    # Symlink real notes into workspace
    for src in REAL_NOTES_DIR.glob("*.md"):
        (ws / "notes" / src.name).symlink_to(src)

    result = _run_process("ingest", "--all", "--no-confirm", cwd=ws)
    assert result.returncode == 0, result.stderr

    entries = list((ws / "kb" / "concepts").glob("*.md"))
    assert len(entries) >= 14, f"Expected >=14 entries, got {len(entries)}"
