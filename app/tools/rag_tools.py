from typing import Optional

from app.rag.qa import build_sources, filter_reliable_results


def get_settings():
    from app.core.config import get_settings as _get_settings

    return _get_settings()


def _search_knowledge_base(query: str, top_k: Optional[int] = None) -> list:
    from app.rag.vector_store import search_knowledge_base as _search

    return _search(query, top_k=top_k)


def search_knowledge_base(query: str, device_code: Optional[str] = None) -> dict:
    """Search the RAG knowledge base and return a model-friendly dict."""
    settings = get_settings()
    search_query = f"{device_code} {query}" if device_code else query

    try:
        results = _search_knowledge_base(search_query, top_k=settings.top_k)
        reliable_results = filter_reliable_results(results, settings.similarity_threshold)
        sources = build_sources(reliable_results)
    except Exception as exc:
        return {
            "success": False,
            "tool_name": "search_knowledge_base",
            "query": query,
            "device_code": device_code,
            "sources": [],
            "summary": f"知识库检索失败：{exc}",
        }

    if not sources:
        return {
            "success": True,
            "tool_name": "search_knowledge_base",
            "query": query,
            "device_code": device_code,
            "sources": [],
            "summary": "知识库未检索到高于阈值的可靠依据。",
        }

    return {
        "success": True,
        "tool_name": "search_knowledge_base",
        "query": query,
        "device_code": device_code,
        "sources": sources,
        "summary": "检索到若干条知识库片段。",
    }
