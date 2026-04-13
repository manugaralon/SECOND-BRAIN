"""KB-06: CLAUDE.md structural validation (unit, no LLM)."""
from pathlib import Path

CLAUDE_MD = Path("CLAUDE.md")

REQUIRED_SECTIONS = [
    "## KB Layout",
    "## Session Initialization",
    "## Query Protocol",
    "## Gap Detection",
    "## Contradiction Rule",
    "## Response Structure",
]

REQUIRED_PATHS = [
    "kb/personal/",
    "kb/concepts/",
    "kb/INDEX.md",
]

REQUIRED_DOMAINS = [
    "fisioterapia", "ia", "finanzas", "trading",
    "esoterismo", "psicologia", "deportes", "personal",
]


def test_claude_md_exists():
    """CLAUDE.md must exist at project root."""
    assert CLAUDE_MD.exists(), "CLAUDE.md not found at project root"


def test_claude_md_sections():
    """CLAUDE.md must contain all required oracle sections."""
    content = CLAUDE_MD.read_text()
    for section in REQUIRED_SECTIONS:
        assert section in content, f"Missing section: {section}"


def test_claude_md_kb_paths():
    """CLAUDE.md must reference all KB paths."""
    content = CLAUDE_MD.read_text()
    for path in REQUIRED_PATHS:
        assert path in content, f"Missing KB path reference: {path}"


def test_claude_md_domains():
    """CLAUDE.md must list all 8 valid domains."""
    content = CLAUDE_MD.read_text()
    for domain in REQUIRED_DOMAINS:
        assert domain in content, f"Missing domain: {domain}"


def test_claude_md_gap_threshold():
    """CLAUDE.md must specify a numeric gap threshold."""
    content = CLAUDE_MD.read_text()
    assert "cobertura escasa" in content, "Missing gap detection phrase 'cobertura escasa'"


def test_claude_md_imperative_language():
    """CLAUDE.md must use imperative language (must/never/always), not advisory (should/try)."""
    content = CLAUDE_MD.read_text().lower()
    # Must have at least some imperative terms
    imperative_count = content.count("must") + content.count("never") + content.count("always")
    assert imperative_count >= 5, f"Too few imperative terms ({imperative_count}). CLAUDE.md should use 'must', 'never', 'always' — not 'should', 'try to'."
