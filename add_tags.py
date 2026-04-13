#!/usr/bin/env python3
"""
Adds tags: [domain] to frontmatter of all KB .md files.
Skips files that already have tags.
"""
import os
import re

KB_DIRS = [
    "/home/manuel/Desktop/PROJECTS/SECONDBRAIN/kb/concepts",
    "/home/manuel/Desktop/PROJECTS/SECONDBRAIN/kb/personal",
]

def process_file(path):
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    # Must start with ---
    if not content.startswith("---"):
        print(f"  SKIP (no frontmatter): {os.path.basename(path)}")
        return

    # Find closing ---
    end = content.find("\n---", 3)
    if end == -1:
        print(f"  SKIP (malformed frontmatter): {os.path.basename(path)}")
        return

    frontmatter = content[3:end]
    body = content[end:]

    # Already has tags
    if re.search(r"^tags:", frontmatter, re.MULTILINE):
        print(f"  SKIP (already has tags): {os.path.basename(path)}")
        return

    # Extract domain value
    match = re.search(r'^domain:\s*["\']?(\w+)["\']?', frontmatter, re.MULTILINE)
    if not match:
        print(f"  SKIP (no domain): {os.path.basename(path)}")
        return

    domain = match.group(1)

    # Also extract confidence to add low-confidence tag if needed
    conf_match = re.search(r'^confidence:\s*([\d.]+)', frontmatter, re.MULTILINE)
    tags = [domain]
    if conf_match and float(conf_match.group(1)) < 0.5:
        tags.append("low-confidence")

    tags_line = f"tags: [{', '.join(tags)}]"
    new_frontmatter = frontmatter.rstrip() + f"\n{tags_line}\n"
    new_content = f"---{new_frontmatter}{body}"

    with open(path, "w", encoding="utf-8") as f:
        f.write(new_content)

    print(f"  OK [{', '.join(tags)}]: {os.path.basename(path)}")

for kb_dir in KB_DIRS:
    for fname in sorted(os.listdir(kb_dir)):
        if fname.endswith(".md"):
            process_file(os.path.join(kb_dir, fname))

print("\nDone.")
