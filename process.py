"""
process.py — Knowledge processor CLI

Subcommands:
    ingest <file>          Process one upstream note → atomic KB entries
    ingest --all           Process all notes in NOTES_DIR
    lint                   Validate kb/concepts/*.md against schema.md

Reads from: /home/manuel/Desktop/PROJECTS/SECONDBRAIN/pipeline/notes/
Writes to:  kb/concepts/
Idempotency log: ./processed.log
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Optional

import frontmatter

# ---------- Constants ----------

REQUIRED_FIELDS: list[str] = [
    "concept", "domain", "confidence", "summary", "sources", "last_updated"
]

VALID_DOMAINS: set[str] = {
    "fisioterapia", "ia", "finanzas", "trading",
    "esoterismo", "psicologia", "deportes", "personal",
}

NOTES_DIR: Path = Path("/home/manuel/Desktop/PROJECTS/SECONDBRAIN/pipeline/notes")
KB_CONCEPTS_DIR: Path = Path("kb/concepts")
KB_PERSONAL_DIR: Path = Path("kb/personal")
PROCESSED_LOG: Path = Path("processed.log")
LOW_CONFIDENCE_THRESHOLD: float = 0.5

CHROMA_PATH: str = ".chroma"
VECTOR_COLLECTION_NAME: str = "secondbrain"
VECTOR_EMBEDDING_MODEL: str = "paraphrase-multilingual-MiniLM-L12-v2"

TOPIC_TO_DOMAIN: dict[str, str] = {
    "claude-env": "ia",
}

OPTIONAL_LIST_FIELDS = ("contradicts", "extends", "gaps")

GROQ_MODEL_PRIMARY = "llama-3.3-70b-versatile"
GROQ_MODEL_FALLBACK = "llama-3.1-8b-instant"
GROQ_MODEL_EXTRACTION = GROQ_MODEL_PRIMARY  # kept for backward compat

# Keys in priority order — add more by appending GROQ_API_KEY_2, GROQ_API_KEY_3 to .env
def _load_groq_keys() -> list[str]:
    keys = []
    for var in ("GROQ_API_KEY", "GROQ_API_KEY_2", "GROQ_API_KEY_3"):
        v = os.getenv(var, "").strip()
        if v:
            keys.append(v)
    return keys

# Build client rotation: (key, model) pairs in priority order
# Priority: all keys with primary model first, then all keys with fallback model
def _groq_clients() -> list[tuple[str, str]]:
    keys = _load_groq_keys()
    if not keys:
        return []
    combos = []
    for key in keys:
        combos.append((key, GROQ_MODEL_PRIMARY))
    for key in keys:
        combos.append((key, GROQ_MODEL_FALLBACK))
    return combos

EXTRACTION_SYSTEM_PROMPT = """You are a knowledge extraction engine. Given a note (Instagram carousel or video transcription), identify all distinct, atomic concepts it teaches.

For each concept output:
- concept: kebab-case slug, unique, descriptive (e.g. "prompting-chain-of-thought")
- summary: one sentence asserting what this entry states
- domain: one of [fisioterapia, ia, finanzas, trading, esoterismo, psicologia, deportes, personal]
- confidence: float 0.0-1.0
- gaps: list of strings for unknowns (omit or empty list if none)
- body: a markdown bullet list (3-6 bullets) with the concrete claims of this concept

Confidence scale:
- 0.9+: multiple independent sources agree, no contradictions
- 0.7-0.9: single high-quality source or multiple weak sources
- 0.5-0.7: contested, single influencer, or unverified claim
- below 0.5: explicitly contradicted or speculative

Rules:
- Carousels: ignore the last "follow/like/swipe" CTA slide
- One note may yield 0, 1, or N concepts — pure self-promotion → 0 concepts
- Concepts must be ATOMIC: one assertion per concept, not a bundle
- Output JSON: {"concepts": [{"concept": ..., "summary": ..., "domain": ..., "confidence": ..., "gaps": [...], "body": "..."}, ...]}
"""

CONTRADICTION_SYSTEM_PROMPT = """You are a knowledge graph integrity checker. Given a new KB entry and a list of existing same-domain entries, identify which existing entries semantically contradict the new entry.

A contradiction is when two entries make mutually exclusive claims about the same topic — not just different perspectives or complementary views, but direct logical conflicts (A says X is always true, B says X is never true).

Output JSON: {"contradictions": [{"concept": "existing-slug", "detail": "one sentence describing what specifically conflicts"}, ...]}
If no contradictions found: {"contradictions": []}
"""


# ---------- Index ----------

INDEX_PATH: Path = Path("kb/INDEX.md")

INDEX_HEADER = """\
# Knowledge Base Index

This index is auto-maintained by the processor (`process.py`). Manual edits below the separator comment will be overwritten.

| Slug | Domain | Summary | Path |
|------|--------|---------|------|
"""

INDEX_FOOTER = "\n<!-- Entries below are managed by process.py -->\n"


def rebuild_index(
    concepts_dir: Path = KB_CONCEPTS_DIR,
    personal_dir: Path = KB_PERSONAL_DIR,
    index_path: Path = INDEX_PATH,
) -> int:
    """Regenerate kb/INDEX.md from all .md files in concepts_dir and personal_dir.

    Returns the total number of entries written.
    """
    rows: list[tuple[str, str, str, str]] = []  # (slug, domain, summary, path)

    def _load_dir(directory: Path) -> list[tuple[str, str, str, str]]:
        entries: list[tuple[str, str, str, str]] = []
        if not directory.exists():
            return entries
        for md_path in sorted(directory.glob("*.md")):
            try:
                post = frontmatter.load(str(md_path))
            except Exception as e:
                print(f"[WARN] Could not parse {md_path}: {e}")
                continue
            slug = post.metadata.get("concept", md_path.stem)
            domain = post.metadata.get("domain", "")
            summary = post.metadata.get("summary", "")
            # Escape pipe characters so they don't break the Markdown table
            summary = str(summary).replace("|", "\\|")
            rel_path = str(md_path).replace("\\", "/")
            entries.append((slug, domain, summary, rel_path))
        return entries

    personal_rows = _load_dir(personal_dir)
    concept_rows = _load_dir(concepts_dir)
    rows = personal_rows + concept_rows

    lines = [INDEX_HEADER]
    for slug, domain, summary, path in rows:
        lines.append(f"| {slug} | {domain} | {summary} | {path} |\n")
    lines.append(INDEX_FOOTER)

    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text("".join(lines))
    print(f"[OK] INDEX.md written — {len(rows)} entries ({len(personal_rows)} personal, {len(concept_rows)} concepts)")
    return len(rows)


# ---------- Lint ----------

def lint_entry(path: Path) -> list[str]:
    errors: list[str] = []
    try:
        post = frontmatter.load(str(path))
    except Exception as e:
        return [f"failed to parse frontmatter: {e}"]

    meta = post.metadata

    # 1. Required fields present
    for field in REQUIRED_FIELDS:
        if field not in meta or meta[field] in (None, ""):
            errors.append(f"missing required field '{field}'")

    # 2. Domain enum
    if "domain" in meta and meta["domain"] not in VALID_DOMAINS:
        errors.append(
            f"invalid domain '{meta['domain']}' — must be one of {sorted(VALID_DOMAINS)}"
        )

    # 3. Confidence range
    if "confidence" in meta and meta["confidence"] is not None:
        try:
            c = float(meta["confidence"])
            if not (0.0 <= c <= 1.0):
                errors.append(f"confidence {c} out of range [0.0, 1.0]")
        except (TypeError, ValueError):
            errors.append("confidence must be a float in [0.0, 1.0]")

    # 4. Sources non-empty list with note|url + date
    if "sources" in meta:
        sources = meta["sources"]
        if not isinstance(sources, list) or len(sources) == 0:
            errors.append("sources must be a non-empty list")
        else:
            for i, src in enumerate(sources):
                if not isinstance(src, dict):
                    errors.append(f"sources[{i}] must be a mapping")
                    continue
                if "note" not in src and "url" not in src:
                    errors.append(f"sources[{i}] missing 'note' or 'url' key")
                if "date" not in src:
                    errors.append(f"sources[{i}] missing 'date' key")

    # 5. last_updated YYYY-MM-DD
    if "last_updated" in meta and meta["last_updated"] is not None:
        lu = meta["last_updated"]
        if isinstance(lu, date):
            pass  # OK — python-frontmatter parses YAML dates as datetime.date
        else:
            try:
                datetime.strptime(str(lu), "%Y-%m-%d")
            except ValueError:
                errors.append(f"last_updated '{lu}' is not YYYY-MM-DD")

    # 6. Slug-filename match
    expected_slug = path.stem
    if "concept" in meta and meta["concept"] != expected_slug:
        errors.append(
            f"concept slug '{meta['concept']}' does not match filename '{expected_slug}'"
        )

    # 7. Forbidden empty optional arrays
    for opt_field in OPTIONAL_LIST_FIELDS:
        if opt_field in meta and meta[opt_field] == []:
            errors.append(
                f"empty {opt_field} array not allowed — omit field if not applicable"
            )

    return errors


def lint_all(kb_dir: Path) -> dict[Path, list[str]]:
    results: dict[Path, list[str]] = {}
    for path in sorted(kb_dir.glob("*.md")):
        results[path] = lint_entry(path)
    return results


# ---------- Ingest helpers ----------

def load_note(path: Path) -> frontmatter.Post:
    return frontmatter.load(str(path))


def load_processed_slugs(log_path: Path) -> set[str]:
    if not log_path.exists():
        return set()
    slugs: set[str] = set()
    with open(log_path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
                slugs.add(record["slug"])
            except (json.JSONDecodeError, KeyError):
                continue
    return slugs


def append_processed(
    log_path: Path,
    slug: str,
    n_created: int,
    status: str,
    **extra,
) -> None:
    record = {
        "slug": slug,
        "processed_at": datetime.now().isoformat(timespec="seconds"),
        "entries_created": n_created,
        "status": status,
    }
    record.update(extra)
    with open(log_path, "a") as f:
        f.write(json.dumps(record) + "\n")


def extract_concepts(note_content: str, note_metadata: dict) -> list[dict]:
    from groq import Groq
    from groq import BadRequestError as GroqBadRequestError, RateLimitError as GroqRateLimitError

    topic = note_metadata.get("topic", "")
    domain_hint = TOPIC_TO_DOMAIN.get(topic, "infer from content")
    user_msg = (
        f"Note metadata: {json.dumps({k: str(v) for k, v in note_metadata.items()}, ensure_ascii=False)}\n"
        f"Suggested domain (override if content disagrees): {domain_hint}\n\n"
        f"--- NOTE BODY ---\n{note_content}"
    )

    last_error: Exception | None = None
    for api_key, model in _groq_clients():
        client = Groq(api_key=api_key)
        common_args = dict(
            model=model,
            messages=[
                {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.1,
        )
        try:
            try:
                response = client.chat.completions.create(
                    response_format={"type": "json_object"},
                    **common_args,
                )
            except GroqBadRequestError:
                response = client.chat.completions.create(**common_args)

            raw = response.choices[0].message.content
            raw_stripped = raw.strip()
            if raw_stripped.startswith("```"):
                lines = raw_stripped.splitlines()
                raw_stripped = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])
            try:
                payload = json.loads(raw_stripped)
            except json.JSONDecodeError as e:
                raise RuntimeError(f"Groq returned invalid JSON: {e}\n{raw[:500]}")
            concepts = payload.get("concepts", [])
            for c in concepts:
                if isinstance(c.get("body"), list):
                    c["body"] = "\n".join(str(item) for item in c["body"])
            if model != GROQ_MODEL_PRIMARY:
                print(f"  [~] Used fallback model ({model})")
            return concepts

        except GroqRateLimitError as e:
            print(f"  [~] Rate limit on {api_key[:12]}... / {model} — trying next")
            last_error = e
            continue

    raise last_error or RuntimeError("No Groq clients available")


def find_contradictions(new_entry: dict, kb_dir: Path) -> list[dict]:
    """Pass 2 LLM call. Compares new_entry against existing same-domain entries.

    Returns list of {concept: str, detail: str} for entries that semantically
    contradict new_entry. Returns [] if no contradictions or kb_dir is empty.

    Excludes the new entry's own slug from comparison to prevent self-contradiction.
    """
    from groq import Groq

    domain = new_entry.get("domain", "")
    if not domain:
        return []

    current_slug = new_entry.get("concept", "")

    # Load existing same-domain entries for comparison, excluding self
    existing: list[dict] = []
    for path in sorted(kb_dir.glob("*.md")):
        try:
            post = frontmatter.load(str(path))
            entry_slug = post.metadata.get("concept", path.stem)
            if post.metadata.get("domain") == domain and entry_slug != current_slug:
                existing.append({
                    "concept": entry_slug,
                    "summary": post.metadata.get("summary", ""),
                })
        except Exception:
            continue

    if not existing:
        return []

    from groq import Groq, RateLimitError as GroqRateLimitError, BadRequestError as GroqBadRequestError

    user_msg = (
        f"New entry:\n"
        f"{json.dumps({'concept': new_entry.get('concept'), 'domain': domain, 'summary': new_entry.get('summary')}, ensure_ascii=False)}\n\n"
        f"Existing {domain} entries to check against:\n"
        f"{json.dumps(existing, ensure_ascii=False)}"
    )

    for api_key, model in _groq_clients():
        client = Groq(api_key=api_key)
        try:
            try:
                response = client.chat.completions.create(
                    model=model,
                    response_format={"type": "json_object"},
                    messages=[
                        {"role": "system", "content": CONTRADICTION_SYSTEM_PROMPT},
                        {"role": "user", "content": user_msg},
                    ],
                    temperature=0.0,
                )
            except GroqBadRequestError:
                response = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": CONTRADICTION_SYSTEM_PROMPT},
                        {"role": "user", "content": user_msg},
                    ],
                    temperature=0.0,
                )
            raw = response.choices[0].message.content
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                return []
            return payload.get("contradictions", [])

        except GroqRateLimitError:
            continue

    print(f"[WARN] find_contradictions — all clients rate-limited, skipping")
    return []


# ---------- Vector Index ----------

def _get_vector_collection(chroma_path: str = CHROMA_PATH):
    """Return (client, collection) tuple with multilingual embedding function."""
    import chromadb
    from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
    client = chromadb.PersistentClient(path=chroma_path)
    ef = SentenceTransformerEmbeddingFunction(model_name=VECTOR_EMBEDDING_MODEL)
    col = client.get_or_create_collection(
        name=VECTOR_COLLECTION_NAME,
        embedding_function=ef,
    )
    return client, col


def upsert_entry(
    slug: str,
    document_text: str,
    domain: str,
    confidence: float,
    chroma_path: str = CHROMA_PATH,
) -> None:
    _, col = _get_vector_collection(chroma_path)
    col.upsert(
        ids=[slug],
        documents=[document_text],
        metadatas=[{"domain": domain, "confidence": float(confidence)}],
    )


def rebuild_vector_index(
    concepts_dir: Path = KB_CONCEPTS_DIR,
    personal_dir: Path = KB_PERSONAL_DIR,
    chroma_path: str = CHROMA_PATH,
) -> int:
    """Full rebuild: delete + recreate collection from all kb/ entries.

    Returns number of entries upserted. Does not modify any kb/ file.
    """
    import chromadb
    from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

    client = chromadb.PersistentClient(path=chroma_path)
    try:
        client.delete_collection(VECTOR_COLLECTION_NAME)
    except Exception:
        pass  # collection may not exist yet
    ef = SentenceTransformerEmbeddingFunction(model_name=VECTOR_EMBEDDING_MODEL)
    col = client.create_collection(
        name=VECTOR_COLLECTION_NAME,
        embedding_function=ef,
    )

    ids: list[str] = []
    docs: list[str] = []
    metas: list[dict] = []
    sources: list[Path] = []
    if concepts_dir.exists():
        sources.extend(sorted(concepts_dir.glob("*.md")))
    if personal_dir.exists():
        sources.extend(sorted(personal_dir.glob("*.md")))

    for md_path in sources:
        post = frontmatter.load(str(md_path))
        slug = post.metadata.get("concept", md_path.stem)
        domain = post.metadata.get("domain", "")
        summary = post.metadata.get("summary", "") or ""
        body = post.content or ""
        document_text = f"{summary}\n{body}".strip() or slug
        ids.append(str(slug))
        docs.append(document_text)
        metas.append({
            "domain": str(domain),
            "confidence": float(post.metadata.get("confidence", 0) or 0),
        })

    if ids:
        col.upsert(ids=ids, documents=docs, metadatas=metas)
    return len(ids)


def _sync_to_vector_index(concept: dict, chroma_path: str = CHROMA_PATH) -> None:
    """Non-critical: upsert one concept into vector index. Never raises."""
    try:
        slug = str(concept["concept"])
        summary = concept.get("summary", "") or ""
        body = concept.get("body", "") or ""
        domain = str(concept.get("domain", ""))
        confidence = float(concept.get("confidence", 0) or 0)
        document_text = f"{summary}\n{body}".strip() or slug
        upsert_entry(slug, document_text, domain, confidence, chroma_path)
    except Exception as e:
        print(f"[WARN] vector index sync failed for {concept.get('concept')}: {e}")


def write_kb_entry(concept_slug: str, data: dict, kb_dir: Path) -> Path:
    kb_dir.mkdir(parents=True, exist_ok=True)
    post = frontmatter.Post(data.get("body", ""))
    post["concept"] = concept_slug
    post["domain"] = data["domain"]
    post["confidence"] = float(data["confidence"])
    post["summary"] = data["summary"]
    post["sources"] = data["sources"]
    post["last_updated"] = date.today().isoformat()

    # Optional fields — only write if non-empty
    for opt in OPTIONAL_LIST_FIELDS:
        value = data.get(opt)
        if value:  # truthy: non-empty list
            post[opt] = value

    out_path = kb_dir / f"{concept_slug}.md"
    out_path.write_text(frontmatter.dumps(post))
    return out_path


def _interactive_confirm(concept: dict) -> tuple[str, Optional[str]]:
    """Returns (action, new_slug). action in {"write", "skip", "rename"}."""
    print(f"\nLow confidence ({concept['confidence']:.2f}): {concept['concept']}")
    print(f"  Summary: {concept['summary']}")
    print(f"  Domain:  {concept['domain']}")
    print("  [w] Write as-is")
    print("  [s] Skip this entry")
    print("  [r] Rename concept slug")
    print("  [q] Quit ingest run")
    choice = input("Choice [w/s/r/q]: ").strip().lower()
    if choice == "w":
        return ("write", None)
    if choice == "s":
        return ("skip", None)
    if choice == "r":
        new_slug = input("New slug: ").strip()
        return ("rename", new_slug or concept["concept"])
    if choice == "q":
        sys.exit(0)
    return ("skip", None)


def ingest_note(
    note_path: Path,
    kb_dir: Path,
    log_path: Path,
    no_confirm: bool = False,
) -> dict:
    note_slug = note_path.stem
    processed = load_processed_slugs(log_path)
    if note_slug in processed:
        print(f"[SKIP] {note_slug} already processed")
        return {"n_created": 0, "n_skipped": 0, "status": "already_processed"}

    post = load_note(note_path)
    concepts = extract_concepts(post.content, post.metadata)

    if not concepts:
        append_processed(log_path, note_slug, 0, "no_concepts_found", contradictions_found=0)
        return {"n_created": 0, "n_skipped": 0, "status": "no_concepts_found"}

    n_created = 0
    n_skipped = 0
    n_contradictions = 0
    for concept in concepts:
        slug = concept.get("concept", "").strip()
        if not slug:
            n_skipped += 1
            continue

        confidence = float(concept.get("confidence", 0))
        if confidence < LOW_CONFIDENCE_THRESHOLD:
            if no_confirm:
                print(f"[SKIP-LOW-CONF] {slug} (confidence={confidence:.2f})")
                n_skipped += 1
                continue
            action, new_slug = _interactive_confirm(concept)
            if action == "skip":
                n_skipped += 1
                continue
            if action == "rename" and new_slug:
                slug = new_slug
                concept["concept"] = new_slug

        # Slug collision check
        target = kb_dir / f"{slug}.md"
        if target.exists():
            print(f"[COLLISION] {slug} already exists — not overwriting")
            n_skipped += 1
            continue

        # Build sources list
        concept["sources"] = [{"note": note_slug, "date": date.today().isoformat()}]

        # Coerce domain via topic mapping if LLM left it unset
        if "domain" not in concept or concept["domain"] not in VALID_DOMAINS:
            concept["domain"] = TOPIC_TO_DOMAIN.get(post.metadata.get("topic", ""), "ia")

        write_kb_entry(slug, concept, kb_dir)
        n_created += 1
        print(f"[WRITE] {slug} (confidence={confidence:.2f})")

        # Pass 2: contradiction detection against existing same-domain entries
        contradictions = find_contradictions(concept, kb_dir)
        if contradictions:
            entry_path = kb_dir / f"{slug}.md"
            written = frontmatter.load(str(entry_path))
            written["contradicts"] = contradictions
            entry_path.write_text(frontmatter.dumps(written))
            slugs_conflicting = [c["concept"] for c in contradictions]
            print(f"[CONTRADICTION] {slug} contradicts: {slugs_conflicting}")
            n_contradictions += 1

    # Log AFTER all writes complete (avoid partial-run race)
    status = "ok" if n_created > 0 else ("all_skipped" if n_skipped > 0 else "no_entries")
    append_processed(
        log_path, note_slug, n_created, status,
        entries_skipped=n_skipped,
        contradictions_found=n_contradictions,
    )
    return {"n_created": n_created, "n_skipped": n_skipped, "status": status}


# ---------- CLI ----------

def _cmd_lint(args: argparse.Namespace) -> int:
    kb_dirs: list[Path] = []
    if args.kb_dir:
        kb_dirs.append(Path(args.kb_dir))
    else:
        kb_dirs.extend([KB_CONCEPTS_DIR, KB_PERSONAL_DIR])

    total_errors = 0
    for kb_dir in kb_dirs:
        if not kb_dir.exists():
            print(f"[WARN] {kb_dir} does not exist, skipping")
            continue
        results = lint_all(kb_dir)
        for path, errors in results.items():
            for err in errors:
                print(f"[ERROR] {path}: {err}")
                total_errors += 1
        print(f"[INFO] {kb_dir}: {len(results)} entries scanned")

    if total_errors > 0:
        print(f"[FAIL] {total_errors} violation(s) found")
        return 1
    print("[OK] no violations")
    return 0


def _cmd_ingest(args: argparse.Namespace) -> int:
    notes_dir = Path(args.notes_dir) if args.notes_dir else NOTES_DIR
    kb_dir = Path(args.kb_dir) if args.kb_dir else KB_CONCEPTS_DIR
    log_path = Path(args.log) if args.log else PROCESSED_LOG

    if args.all:
        note_paths = sorted(notes_dir.glob("*.md"))
        if not note_paths:
            print(f"[ERROR] no notes found in {notes_dir}")
            return 1
    else:
        if not args.file:
            print("[ERROR] either <file> or --all is required")
            return 2
        note_paths = [Path(args.file)]

    total_created = 0
    total_skipped = 0
    for note_path in note_paths:
        try:
            result = ingest_note(note_path, kb_dir, log_path, no_confirm=args.no_confirm)
            total_created += result["n_created"]
            total_skipped += result["n_skipped"]
        except Exception as e:
            print(f"[ERROR] {note_path.name}: {e}")
            append_processed(log_path, note_path.stem, 0, "error", error=str(e), contradictions_found=0)

    # Keep index in sync after every ingest run
    rebuild_index()
    print(f"[DONE] created={total_created} skipped={total_skipped}")
    return 0


def _cmd_rebuild_index(args: argparse.Namespace) -> int:
    concepts_dir = Path(args.concepts_dir) if args.concepts_dir else KB_CONCEPTS_DIR
    personal_dir = Path(args.personal_dir) if args.personal_dir else KB_PERSONAL_DIR
    index_path = Path(args.index_path) if args.index_path else INDEX_PATH
    rebuild_index(concepts_dir, personal_dir, index_path)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="process.py",
        description="Knowledge processor: notes/*.md → kb/concepts/*.md",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_ingest = sub.add_parser("ingest", help="Process upstream notes into KB entries")
    p_ingest.add_argument("file", nargs="?", help="Path to a single note file")
    p_ingest.add_argument("--all", action="store_true", help="Process all notes in NOTES_DIR")
    p_ingest.add_argument("--no-confirm", action="store_true", help="Skip interactive prompts on low confidence")
    p_ingest.add_argument("--notes-dir", default=None, help="Override NOTES_DIR")
    p_ingest.add_argument("--kb-dir", default=None, help="Override KB_CONCEPTS_DIR")
    p_ingest.add_argument("--log", default=None, help="Override processed.log path")
    p_ingest.set_defaults(func=_cmd_ingest)

    p_lint = sub.add_parser("lint", help="Validate kb/ entries against schema")
    p_lint.add_argument("--kb-dir", default=None, help="Lint a specific directory only")
    p_lint.set_defaults(func=_cmd_lint)

    p_rebuild = sub.add_parser("rebuild-index", help="Regenerate kb/INDEX.md from disk")
    p_rebuild.add_argument("--concepts-dir", default=None, help="Override KB_CONCEPTS_DIR")
    p_rebuild.add_argument("--personal-dir", default=None, help="Override KB_PERSONAL_DIR")
    p_rebuild.add_argument("--index-path", default=None, help="Override INDEX_PATH")
    p_rebuild.set_defaults(func=_cmd_rebuild_index)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
