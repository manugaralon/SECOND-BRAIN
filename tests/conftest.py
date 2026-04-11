import shutil
from pathlib import Path
import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def tmp_kb_dir(tmp_path: Path) -> Path:
    """Temporary kb/ directory tree mirroring the real project layout."""
    kb = tmp_path / "kb"
    (kb / "concepts").mkdir(parents=True)
    (kb / "personal").mkdir(parents=True)
    return kb


@pytest.fixture
def sample_note_path() -> Path:
    """Path to the real upstream sample note copied into fixtures."""
    return FIXTURES_DIR / "sample_note.md"


@pytest.fixture
def sample_kb_entry(tmp_kb_dir: Path) -> Path:
    """Drop a known-valid KB entry into tmp_kb_dir/concepts/ and return its path."""
    src = FIXTURES_DIR / "valid_entry.md"
    dst = tmp_kb_dir / "concepts" / "valid_entry.md"
    shutil.copy(src, dst)
    return dst


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES_DIR
