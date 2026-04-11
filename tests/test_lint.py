"""KB-01: lint validation tests (unit, no LLM)."""
import pytest
from pathlib import Path

# This import will fail until Plan 02 creates process.py — that is the RED state.
from process import lint_entry, lint_all, REQUIRED_FIELDS, VALID_DOMAINS


def test_required_fields_constant_matches_schema():
    """REQUIRED_FIELDS must list exactly the 6 required schema fields."""
    assert set(REQUIRED_FIELDS) == {
        "concept", "domain", "confidence", "summary", "sources", "last_updated"
    }


def test_valid_domains_constant_matches_schema():
    """VALID_DOMAINS must list exactly the 8 schema enum values."""
    assert VALID_DOMAINS == {
        "fisioterapia", "ia", "finanzas", "trading",
        "esoterismo", "psicologia", "deportes", "personal",
    }


def test_valid_entry_passes(fixtures_dir: Path):
    """A schema-conformant entry produces zero errors."""
    errors = lint_entry(fixtures_dir / "valid_entry.md")
    assert errors == [], f"Expected no errors, got: {errors}"


def test_lint_catches_missing_field(fixtures_dir: Path):
    """An entry missing 'confidence' must report the missing field."""
    errors = lint_entry(fixtures_dir / "invalid_entry_missing_field.md")
    assert any("confidence" in e for e in errors), errors


def test_lint_catches_empty_array(fixtures_dir: Path):
    """An entry with `gaps: []` must be flagged — schema forbids empty optional arrays."""
    errors = lint_entry(fixtures_dir / "invalid_entry_empty_array.md")
    assert any("gaps" in e for e in errors), errors


def test_lint_catches_slug_mismatch(fixtures_dir: Path):
    """An entry whose 'concept' field does not match the filename must be flagged."""
    errors = lint_entry(fixtures_dir / "invalid_entry_slug_mismatch.md")
    assert any("slug" in e.lower() or "filename" in e.lower() for e in errors), errors


def test_lint_all_returns_dict_of_errors(tmp_kb_dir: Path, sample_kb_entry: Path):
    """lint_all must return a dict mapping path → errors list, with valid entry empty."""
    result = lint_all(tmp_kb_dir / "concepts")
    assert isinstance(result, dict)
    assert sample_kb_entry in result
    assert result[sample_kb_entry] == []
