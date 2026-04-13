"""KB-05: INDEX.md completeness tests (unit, no LLM)."""
import re
from pathlib import Path

KB_CONCEPTS_DIR = Path("kb/concepts")
KB_PERSONAL_DIR = Path("kb/personal")
INDEX_PATH = Path("kb/INDEX.md")


def _parse_index_slugs() -> set[str]:
    """Extract all slugs from the Slug column of INDEX.md."""
    content = INDEX_PATH.read_text()
    slugs = set()
    for line in content.splitlines():
        if line.startswith("|") and not line.startswith("| Slug") and not line.startswith("|---"):
            parts = [p.strip() for p in line.split("|")]
            if len(parts) >= 2 and parts[1]:
                slugs.add(parts[1])
    return slugs


def test_index_file_exists():
    """INDEX.md must exist at kb/INDEX.md."""
    assert INDEX_PATH.exists(), f"{INDEX_PATH} does not exist"


def test_index_contains_all_concepts():
    """Every .md file in kb/concepts/ must have a row in INDEX.md."""
    concept_slugs = {p.stem for p in KB_CONCEPTS_DIR.glob("*.md")}
    index_slugs = _parse_index_slugs()
    missing = concept_slugs - index_slugs
    assert not missing, f"Concepts missing from INDEX.md: {missing}"


def test_index_contains_all_personal():
    """Every .md file in kb/personal/ must have a row in INDEX.md."""
    personal_slugs = {p.stem for p in KB_PERSONAL_DIR.glob("*.md")}
    index_slugs = _parse_index_slugs()
    missing = personal_slugs - index_slugs
    assert not missing, f"Personal entries missing from INDEX.md: {missing}"


def test_index_has_no_orphans():
    """Every slug in INDEX.md must correspond to an existing .md file."""
    all_slugs = {p.stem for p in KB_CONCEPTS_DIR.glob("*.md")} | {p.stem for p in KB_PERSONAL_DIR.glob("*.md")}
    index_slugs = _parse_index_slugs()
    orphans = index_slugs - all_slugs
    assert not orphans, f"INDEX.md has orphan entries: {orphans}"


def test_index_entry_count():
    """INDEX.md must have at least 52 entries (48 concepts + 4 personal)."""
    index_slugs = _parse_index_slugs()
    assert len(index_slugs) >= 52, f"Expected >= 52 entries, got {len(index_slugs)}"
