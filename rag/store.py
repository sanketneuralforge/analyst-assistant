# rag/store.py

import chromadb
from chromadb.utils import embedding_functions
from pathlib import Path

# Persistent storage — survives restarts
CHROMA_PATH = Path("db/chroma")
DOMAIN_COLLECTION = "domain_knowledge"
METHODS_COLLECTION = "statistical_methods"


def get_client() -> chromadb.PersistentClient:
    CHROMA_PATH.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(CHROMA_PATH))


def get_embedding_fn():
    """
    Use sentence-transformers locally — no API call, no cost, no latency.
    all-MiniLM-L6-v2 is the standard choice: fast, small, good enough
    for domain document retrieval where exact semantic match matters less
    than keyword overlap.
    """
    return embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="all-MiniLM-L6-v2"
    )


def get_domain_collection() -> chromadb.Collection:
    client = get_client()
    return client.get_or_create_collection(
        name=DOMAIN_COLLECTION,
        embedding_function=get_embedding_fn(),
        metadata={"hnsw:space": "cosine"},
    )


def get_methods_collection() -> chromadb.Collection:
    client = get_client()
    return client.get_or_create_collection(
        name=METHODS_COLLECTION,
        embedding_function=get_embedding_fn(),
        metadata={"hnsw:space": "cosine"},
    )