# rag/ingest.py

"""
Run once to index all documents:
    uv run python rag/ingest.py

Re-run whenever you add or update documents.
Existing documents with the same ID are updated, not duplicated.
"""

import hashlib
from pathlib import Path
from rag.store import get_domain_collection, get_methods_collection


def file_to_doc_id(path: Path) -> str:
    """Stable ID from file path — same file always gets same ID."""
    return hashlib.md5(str(path).encode()).hexdigest()


def chunk_markdown(text: str, max_chars: int = 1500) -> list[str]:
    """
    Split markdown on ## headers first, then by character limit.
    Preserves semantic coherence — a section stays together
    rather than being split mid-sentence.
    """
    sections = []
    current = []
    current_len = 0

    for line in text.split("\n"):
        if line.startswith("## ") and current_len > 200:
            sections.append("\n".join(current))
            current = [line]
            current_len = len(line)
        else:
            current.append(line)
            current_len += len(line)

        if current_len > max_chars:
            sections.append("\n".join(current))
            current = []
            current_len = 0

    if current:
        sections.append("\n".join(current))

    return [s.strip() for s in sections if s.strip()]


def ingest_domain_docs():
    """Index all files in rag/domain_docs/ into the domain collection."""
    collection = get_domain_collection()
    docs_path = Path("rag/domain_docs")

    if not docs_path.exists():
        print("  [domain] No domain_docs directory found — skipping")
        return

    files = list(docs_path.glob("**/*.md")) + list(docs_path.glob("**/*.txt"))
    if not files:
        print("  [domain] No documents found in domain_docs/")
        return

    total_chunks = 0
    for file_path in files:
        text = file_path.read_text(encoding="utf-8")
        chunks = chunk_markdown(text)

        for i, chunk in enumerate(chunks):
            doc_id = f"{file_to_doc_id(file_path)}_chunk_{i}"
            collection.upsert(
                ids=[doc_id],
                documents=[chunk],
                metadatas=[{
                    "source": str(file_path),
                    "filename": file_path.name,
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                }],
            )
        total_chunks += len(chunks)
        print(f"  [domain] Indexed {file_path.name} → {len(chunks)} chunks")

    print(f"  [domain] Total: {total_chunks} chunks across {len(files)} files")


def ingest_method_cards():
    """Index all files in rag/method_cards/ into the methods collection."""
    collection = get_methods_collection()
    cards_path = Path("rag/method_cards")

    if not cards_path.exists():
        print("  [methods] No method_cards directory found — skipping")
        return

    files = list(cards_path.glob("**/*.md")) + list(cards_path.glob("**/*.txt"))
    if not files:
        print("  [methods] No method cards found")
        return

    total_chunks = 0
    for file_path in files:
        text = file_path.read_text(encoding="utf-8")
        chunks = chunk_markdown(text)

        for i, chunk in enumerate(chunks):
            doc_id = f"{file_to_doc_id(file_path)}_chunk_{i}"
            collection.upsert(
                ids=[doc_id],
                documents=[chunk],
                metadatas=[{
                    "source": str(file_path),
                    "filename": file_path.name,
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                    "method_name": file_path.stem.replace("_", " ").title(),
                }],
            )
        total_chunks += len(chunks)
        print(f"  [methods] Indexed {file_path.name} → {len(chunks)} chunks")

    print(f"  [methods] Total: {total_chunks} chunks across {len(files)} files")


def ingest_uploaded_file(file_path: Path, store: str = "domain") -> int:
    """
    Ingest a single uploaded file at runtime — called from Streamlit UI
    when a user uploads a document during a session.

    store: "domain" or "methods"
    Returns: number of chunks indexed
    """
    collection = (
        get_domain_collection() if store == "domain"
        else get_methods_collection()
    )

    text = file_path.read_text(encoding="utf-8")
    chunks = chunk_markdown(text)

    for i, chunk in enumerate(chunks):
        doc_id = f"{file_to_doc_id(file_path)}_chunk_{i}"
        collection.upsert(
            ids=[doc_id],
            documents=[chunk],
            metadatas=[{
                "source": str(file_path),
                "filename": file_path.name,
                "chunk_index": i,
                "total_chunks": len(chunks),
                "uploaded_at_runtime": True,
            }],
        )

    return len(chunks)


def ingest_typed_context(
    text: str,
    source_label: str = "analyst_typed_context",
    store: str = "domain",
) -> int:
    """
    Index free-text typed by the analyst directly into ChromaDB.
    Called when ContextBrief is submitted with analyst_context filled.

    Uses content-based ID so re-submitting the same text doesn't
    create duplicates — upsert overwrites cleanly.
    """
    if not text.strip():
        return 0

    collection = (
        get_domain_collection() if store == "domain"
        else get_methods_collection()
    )

    chunks = chunk_markdown(text)

    for i, chunk in enumerate(chunks):
        content_hash = hashlib.md5(
            f"{source_label}_{chunk}".encode()
        ).hexdigest()
        doc_id = f"typed_{content_hash}_chunk_{i}"

        collection.upsert(
            ids=[doc_id],
            documents=[chunk],
            metadatas=[{
                "source": source_label,
                "filename": "analyst_typed_context",
                "chunk_index": i,
                "total_chunks": len(chunks),
                "is_typed_context": True,
            }],
        )

    return len(chunks)


if __name__ == "__main__":
    print("\nIngesting documents into ChromaDB...")
    print("=" * 50)
    ingest_domain_docs()
    print()
    ingest_method_cards()
    print("=" * 50)
    print("Ingestion complete.\n")