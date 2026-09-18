from typing import Optional


COLLECTION_NAME = "industrial_maintenance_docs"


def distance_to_similarity_score(distance: float) -> float:
    """Convert Chroma distance to a normalized score where higher is better."""
    distance = max(float(distance), 0.0)
    return 1 / (1 + distance)


def get_vector_store():
    from langchain_chroma import Chroma
    from app.core.config import get_settings
    from app.core.llm import get_embedding_model

    settings = get_settings()
    return Chroma(
        collection_name=COLLECTION_NAME,
        persist_directory=str(settings.chroma_persist_dir),
        embedding_function=get_embedding_model(),
    )


def add_documents_to_store(documents) -> int:
    if not documents:
        return 0
    vector_store = get_vector_store()
    vector_store.add_documents(documents)
    # Chroma persists automatically in recent versions; keep compatibility with older ones.
    if hasattr(vector_store, "persist"):
        vector_store.persist()
    return len(documents)


def search_knowledge_base(query: str, top_k: Optional[int] = None) -> list:
    from app.core.config import get_settings

    settings = get_settings()
    resolved_top_k = top_k or settings.top_k
    try:
        vector_store = get_vector_store()
        docs_with_distance = vector_store.similarity_search_with_score(query, k=resolved_top_k)
    except Exception:
        if not settings.offline_fallback_enabled:
            raise
        from app.rag.local_search import search_sample_documents_locally

        return search_sample_documents_locally(query, top_k=resolved_top_k)

    results = []
    for document, distance in docs_with_distance:
        metadata = dict(document.metadata)
        results.append(
            {
                "content": document.page_content,
                "metadata": metadata,
                "similarity_score": distance_to_similarity_score(distance),
                "retrieval_mode": "chroma_embedding",
            }
        )
    return sorted(results, key=lambda item: item["similarity_score"], reverse=True)
