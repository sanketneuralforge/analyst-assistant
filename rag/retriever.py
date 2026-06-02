# rag/retriever.py

from rag.store import get_domain_collection, get_methods_collection

# Similarity threshold — chunks below this score are not returned.
# 0.45 is deliberately loose for domain docs (you want broad context).
# 0.55 is tighter for methods (you want the right technique, not just similar).
DOMAIN_THRESHOLD = 0.45
METHODS_THRESHOLD = 0.55


def retrieve_domain_context(
    query: str,
    n_results: int = 3,
) -> str:
    """
    Retrieve relevant domain knowledge for a given query.
    Called at session start and injected into all mode prompts.
    
    Returns a formatted string block ready for prompt injection.
    Returns empty string if nothing relevant found — never injects noise.
    """
    collection = get_domain_collection()

    if collection.count() == 0:
        return ""

    results = collection.query(
        query_texts=[query],
        n_results=min(n_results, collection.count()),
        include=["documents", "metadatas", "distances"],
    )

    if not results["documents"] or not results["documents"][0]:
        return ""

    chunks = []
    for doc, meta, distance in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        # ChromaDB cosine distance: 0 = identical, 2 = opposite
        # Convert to similarity: 1 - distance/2
        similarity = 1 - (distance / 2)
        if similarity >= DOMAIN_THRESHOLD:
            source = meta.get("filename", "unknown")
            chunks.append(f"[{source}]\n{doc}")

    if not chunks:
        return ""

    return (
        "## RETRIEVED DOMAIN KNOWLEDGE\n"
        "The following context was automatically retrieved from your "
        "domain documents. Use it to ground your analysis.\n\n"
        + "\n\n---\n\n".join(chunks)
    )


def retrieve_statistical_method(
    query: str,
    n_results: int = 2,
) -> str:
    """
    Retrieve the most relevant statistical method for a given 
    analytical question. Called in Mode 2 before drafting code.
    
    Returns a formatted string block ready for prompt injection.
    Returns empty string if collection is empty or nothing relevant.
    """
    collection = get_methods_collection()

    if collection.count() == 0:
        return ""

    results = collection.query(
        query_texts=[query],
        n_results=min(n_results, collection.count()),
        include=["documents", "metadatas", "distances"],
    )

    if not results["documents"] or not results["documents"][0]:
        return ""

    chunks = []
    for doc, meta, distance in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        similarity = 1 - (distance / 2)
        if similarity >= METHODS_THRESHOLD:
            method = meta.get("method_name", meta.get("filename", "unknown"))
            chunks.append(f"[Method: {method}]\n{doc}")

    if not chunks:
        return ""

    return (
        "## RETRIEVED STATISTICAL METHODS\n"
        "The following method(s) were retrieved as relevant to this "
        "analytical question. Use the appropriate method and its "
        "Python template when drafting code.\n\n"
        + "\n\n---\n\n".join(chunks)
    )


def retrieve_causal_guidance(query: str) -> str:
    """
    Specialized retrieval for causal inference questions.
    Combines domain context + method retrieval into one call.
    Used when Mode 1 detects causal language in the user's input.
    """
    domain = retrieve_domain_context(query, n_results=2)
    methods = retrieve_statistical_method(query, n_results=2)

    parts = [p for p in [domain, methods] if p]
    return "\n\n".join(parts)