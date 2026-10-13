from typing import Optional

from app.rag.qa import build_sources, filter_reliable_results


def get_settings():
    from app.core.config import get_settings as _get_settings

    return _get_settings()


def _search_knowledge_base(query: str, top_k: Optional[int] = None) -> list:
    from app.rag.vector_store import search_knowledge_base as _search

    return _search(query, top_k=top_k)


def _local_keyword_fallback(search_query: str, settings) -> list:
    """稠密检索无可靠命中时，用本地关键词检索补检，提升召回。

    仅当 embedding 检索结果全部低于阈值时触发；本地检索使用离线阈值
    （offline_similarity_threshold），结果标记为 local_keyword 模式。
    """
    try:
        from app.rag.local_search import search_sample_documents_locally

        local_results = search_sample_documents_locally(
            search_query, top_k=settings.top_k
        )
        return filter_reliable_results(
            local_results, settings.similarity_threshold
        )
    except Exception:
        return []


def search_knowledge_base(query: str, device_code: Optional[str] = None) -> dict:
    """Search the RAG knowledge base and return a model-friendly dict."""
    settings = get_settings()
    search_query = f"{device_code} {query}" if device_code else query

    try:
        results = _search_knowledge_base(search_query, top_k=settings.top_k)
        reliable_results = filter_reliable_results(results, settings.similarity_threshold)
    except Exception as exc:
        return {
            "success": False,
            "tool_name": "search_knowledge_base",
            "query": query,
            "device_code": device_code,
            "sources": [],
            "summary": f"知识库检索失败：{exc}",
        }

    if not reliable_results:
        reliable_results = _local_keyword_fallback(
            search_query, settings
        )

    sources = build_sources(reliable_results)

    if not sources:
        return {
            "success": True,
            "tool_name": "search_knowledge_base",
            "query": query,
            "device_code": device_code,
            "sources": [],
            "summary": "知识库未检索到高于阈值的可靠依据。",
        }

    retrieval_mode = {
        item.get("retrieval_mode")
        for item in reliable_results
    }
    mode_note = (
        "（含本地关键词兜底检索）"
        if "local_keyword" in retrieval_mode
        else ""
    )

    return {
        "success": True,
        "tool_name": "search_knowledge_base",
        "query": query,
        "device_code": device_code,
        "sources": sources,
        "summary": f"检索到若干条知识库片段{mode_note}。",
    }
