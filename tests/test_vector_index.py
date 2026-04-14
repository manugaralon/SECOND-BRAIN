"""Phase 4 — semantic search (vector index) tests.

All tests are integration: they exercise the real chromadb + sentence-transformers
stack against a temp .chroma dir. The first run downloads the multilingual model
(~120MB). CI/offline runs should deselect with -m "not integration".
"""
import os
import shutil
from pathlib import Path

import frontmatter
import pytest

pytestmark = pytest.mark.integration

COLLECTION_NAME = "secondbrain"
VECTOR_EMBEDDING_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"


@pytest.fixture
def vector_workspace(tmp_path: Path) -> dict:
    """Temp workspace with kb/concepts, kb/personal, and a dedicated .chroma dir."""
    ws = tmp_path / "ws"
    (ws / "kb" / "concepts").mkdir(parents=True)
    (ws / "kb" / "personal").mkdir(parents=True)
    chroma = ws / ".chroma"
    return {"ws": ws, "concepts": ws / "kb" / "concepts",
            "personal": ws / "kb" / "personal", "chroma": chroma}


def _write_entry(path: Path, slug: str, domain: str, summary: str,
                 body: str = "", confidence: float = 0.9) -> None:
    post = frontmatter.Post(body)
    post["concept"] = slug
    post["domain"] = domain
    post["confidence"] = confidence
    post["summary"] = summary
    post["sources"] = [{"note": "test", "date": "2026-04-13"}]
    post["last_updated"] = "2026-04-13"
    (path / f"{slug}.md").write_text(frontmatter.dumps(post))


def test_collection_populated(vector_workspace):
    """SC-1: rebuild_vector_index populates collection with the correct count."""
    from process import rebuild_vector_index  # noqa: E402
    ws = vector_workspace
    _write_entry(ws["concepts"], "slug-a", "fisioterapia", "summary a", "body a")
    _write_entry(ws["concepts"], "slug-b", "ia", "summary b", "body b")
    _write_entry(ws["personal"], "slug-c", "personal", "summary c", "body c")

    count = rebuild_vector_index(
        concepts_dir=ws["concepts"],
        personal_dir=ws["personal"],
        chroma_path=str(ws["chroma"]),
    )
    assert count == 3

    import chromadb
    from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
    client = chromadb.PersistentClient(path=str(ws["chroma"]))
    ef = SentenceTransformerEmbeddingFunction(model_name=VECTOR_EMBEDDING_MODEL)
    col = client.get_or_create_collection(COLLECTION_NAME, embedding_function=ef)
    got = col.get()
    assert set(got["ids"]) == {"slug-a", "slug-b", "slug-c"}


def test_sync_on_ingest(vector_workspace):
    """SC-1 sync: after write_kb_entry + _sync_to_vector_index, slug is queryable."""
    from process import write_kb_entry, _sync_to_vector_index  # noqa: E402
    ws = vector_workspace
    data = {
        "domain": "fisioterapia",
        "confidence": 0.9,
        "summary": "test sync",
        "sources": [{"note": "n", "date": "2026-04-13"}],
        "body": "body-of-sync",
    }
    write_kb_entry("sync-slug", data, ws["concepts"])
    _sync_to_vector_index(
        {"concept": "sync-slug", "domain": "fisioterapia",
         "confidence": 0.9, "summary": "test sync", "body": "body-of-sync"},
        chroma_path=str(ws["chroma"]),
    )
    import chromadb
    from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
    client = chromadb.PersistentClient(path=str(ws["chroma"]))
    ef = SentenceTransformerEmbeddingFunction(model_name=VECTOR_EMBEDDING_MODEL)
    col = client.get_or_create_collection(COLLECTION_NAME, embedding_function=ef)
    got = col.get(ids=["sync-slug"])
    assert "sync-slug" in got["ids"]


def test_query_returns_slugs(vector_workspace):
    """SC-2: query_vector_index returns list[str] of slugs filtered by domain."""
    from process import rebuild_vector_index, query_vector_index  # noqa: E402
    ws = vector_workspace
    _write_entry(ws["concepts"], "espalda-ejercicios", "fisioterapia",
                 "ejercicios para fortalecer la espalda")
    _write_entry(ws["concepts"], "trading-basics", "trading",
                 "introduccion a trading")
    rebuild_vector_index(
        concepts_dir=ws["concepts"], personal_dir=ws["personal"],
        chroma_path=str(ws["chroma"]),
    )
    slugs = query_vector_index(
        query="ejercicios espalda", domains=["fisioterapia"],
        n_results=5, chroma_path=str(ws["chroma"]),
    )
    assert isinstance(slugs, list)
    assert all(isinstance(s, str) for s in slugs)
    assert "espalda-ejercicios" in slugs
    assert "trading-basics" not in slugs  # domain filter enforced


def test_oracle_slug_resolution(vector_workspace):
    """Every slug returned by query_vector_index must resolve to kb/concepts/{slug}.md."""
    from process import rebuild_vector_index, query_vector_index  # noqa: E402
    ws = vector_workspace
    _write_entry(ws["concepts"], "foo-bar", "ia", "summary foo bar")
    rebuild_vector_index(
        concepts_dir=ws["concepts"], personal_dir=ws["personal"],
        chroma_path=str(ws["chroma"]),
    )
    slugs = query_vector_index(
        query="foo bar", domains=["ia"], n_results=3,
        chroma_path=str(ws["chroma"]),
    )
    for slug in slugs:
        assert (ws["concepts"] / f"{slug}.md").exists() or \
               (ws["personal"] / f"{slug}.md").exists()


def test_kb_files_untouched(vector_workspace):
    """SC-3: rebuild_vector_index must not modify any kb/ file."""
    from process import rebuild_vector_index  # noqa: E402
    ws = vector_workspace
    _write_entry(ws["concepts"], "untouched-a", "ia", "summary a")
    _write_entry(ws["personal"], "untouched-b", "personal", "summary b")
    all_files = list(ws["concepts"].glob("*.md")) + list(ws["personal"].glob("*.md"))
    snapshot = {p: (p.stat().st_mtime_ns, p.read_bytes()) for p in all_files}

    rebuild_vector_index(
        concepts_dir=ws["concepts"], personal_dir=ws["personal"],
        chroma_path=str(ws["chroma"]),
    )
    for p, (mtime, contents) in snapshot.items():
        assert p.stat().st_mtime_ns == mtime, f"{p} mtime changed"
        assert p.read_bytes() == contents, f"{p} contents changed"
