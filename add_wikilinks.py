#!/usr/bin/env python3
"""
add_wikilinks.py — Adds [[wikilinks]] to KB entries based on extends/contradicts frontmatter.
Also adds domain-based wikilinks to related concepts (same domain).
Run from: /home/manuel/Desktop/PROJECTS/SECONDBRAIN/
"""
import os
import re
from pathlib import Path

import frontmatter

KB_DIRS = [
    Path("kb/concepts"),
    Path("kb/personal"),
]

def slug_to_wikilink(slug: str) -> str:
    return f"[[{slug}]]"

def get_all_slugs() -> dict[str, Path]:
    """Returns slug -> path mapping for all KB files."""
    slugs = {}
    for d in KB_DIRS:
        for f in d.glob("*.md"):
            slug = f.stem
            slugs[slug] = f
    return slugs

def build_relations_section(post: frontmatter.Post, all_slugs: dict) -> str | None:
    """Builds a ## Relations section from extends/contradicts fields."""
    lines = []

    extends = post.get("extends") or []
    contradicts = post.get("contradicts") or []

    if extends:
        links = []
        for item in extends:
            if isinstance(item, dict):
                slug = item.get("concept", "")
            else:
                slug = str(item)
            if slug and slug in all_slugs:
                links.append(slug_to_wikilink(slug))
        if links:
            lines.append(f"Extends: {' · '.join(links)}")

    if contradicts:
        links = []
        for item in contradicts:
            if isinstance(item, dict):
                slug = item.get("concept", "")
            else:
                slug = str(item)
            if slug and slug in all_slugs:
                links.append(slug_to_wikilink(slug))
        if links:
            lines.append(f"Contradicts: {' · '.join(links)}")

    if not lines:
        return None
    return "## Relations\n\n" + "\n".join(lines)

def process_file(path: Path, all_slugs: dict) -> bool:
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    post = frontmatter.loads(content)
    relations = build_relations_section(post, all_slugs)

    if not relations:
        return False

    # Check if Relations section already exists
    if "## Relations" in post.content:
        return False

    # Append to body
    body = post.content.rstrip()
    new_body = body + f"\n\n{relations}\n"
    post.content = new_body

    with open(path, "w", encoding="utf-8") as f:
        f.write(frontmatter.dumps(post))

    return True

def main():
    os.chdir(Path(__file__).parent)
    all_slugs = get_all_slugs()
    print(f"Found {len(all_slugs)} KB entries\n")

    modified = 0
    skipped = 0
    for d in KB_DIRS:
        for f in sorted(d.glob("*.md")):
            changed = process_file(f, all_slugs)
            if changed:
                print(f"  LINKED: {f}")
                modified += 1
            else:
                skipped += 1

    print(f"\nDone. {modified} files updated, {skipped} skipped (no relations or already linked).")

if __name__ == "__main__":
    main()
