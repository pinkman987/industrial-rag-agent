NO_EVIDENCE_PREFIX = "知识库未找到直接依据，以下仅为通用排查建议"


def filter_reliable_results(results: list, threshold: float) -> list:
    from app.core.config import get_settings

    offline_threshold = get_settings().offline_similarity_threshold
    return [
        item
        for item in results
        if item.get("similarity_score", 0)
        >= (offline_threshold if item.get("retrieval_mode") == "local_keyword" else threshold)
    ]


def build_no_evidence_answer(question: str) -> str:
    return (
        f"{NO_EVIDENCE_PREFIX}\n\n"
        f"问题：{question}\n\n"
        "通用建议：\n"
        "1. 先确认设备已停机或处于安全维护状态，避免带故障继续运行。\n"
        "2. 记录报警码、报警时间、设备状态、操作员动作和现场环境。\n"
        "3. 按电源、传感器、执行机构、机械负载、控制参数的顺序逐项排查。\n"
        "4. 若涉及过热、过载、异响或安全联锁，应联系设备负责人复核后再复机。"
    )


def _source_from_result(result: dict) -> dict:
    metadata = result.get("metadata", {})
    content = result.get("content", "")
    preview = content.replace("\n", " ")[:180]
    return {
        "file_name": metadata.get("file_name", ""),
        "page": metadata.get("page"),
        "chunk_index": metadata.get("chunk_index"),
        "similarity_score": round(float(result.get("similarity_score", 0)), 4),
        "content_preview": preview,
    }


def build_sources(results: list) -> list:
    return [_source_from_result(result) for result in results]


def _build_context(results: list) -> str:
    blocks = []
    for index, result in enumerate(results, start=1):
        source = _source_from_result(result)
        blocks.append(
            "[来源{index}] file_name={file_name}, page={page}, chunk_index={chunk_index}, "
            "similarity_score={similarity_score}\n{content}".format(index=index, **source, content=result["content"])
        )
    return "\n\n".join(blocks)


def _call_llm(question: str, reliable_results: list) -> str:
    from app.core.llm import get_chat_model

    prompt = f"""
你是制造业设备运维知识库助手。请只基于给定知识库内容回答问题。

要求：
1. 回答必须聚焦设备故障原因、排查步骤和维修建议。
2. 不要编造知识库之外的引用。
3. 如果知识库内容不足，请明确说明不足。

知识库内容：
{_build_context(reliable_results)}

用户问题：
{question}
"""
    response = get_chat_model().invoke(prompt)
    return getattr(response, "content", str(response))


def build_offline_extract_answer(question: str, reliable_results: list) -> str:
    """Build a traceable demo answer when the configured chat API is unavailable."""
    evidence = []
    for index, result in enumerate(reliable_results[:4], start=1):
        metadata = result.get("metadata", {})
        lines = [line.strip() for line in result.get("content", "").splitlines() if line.strip()]
        excerpt = " ".join(lines[:6])[:500]
        evidence.append(f"{index}. {excerpt}（来源：{metadata.get('file_name', '未知文件')}）")
    return (
        "当前为本地离线演示回答：外部模型服务不可用，以下内容直接摘取自本地知识库，"
        "未进行大模型扩写。\n\n"
        f"问题：{question}\n\n"
        "检索依据：\n"
        + "\n".join(evidence)
        + "\n\n建议按照上述文档中的故障原因、排查步骤和安全要求逐项核对；"
        "涉及带电、旋转或高温部件时，应先停机并执行现场安全规程。"
    )


def answer_question(question: str) -> dict:
    from app.core.config import get_settings
    from app.rag.vector_store import search_knowledge_base

    settings = get_settings()
    results = search_knowledge_base(question, top_k=settings.top_k)
    reliable_results = filter_reliable_results(results, settings.similarity_threshold)

    if not reliable_results:
        return {
            "message": "未检索到高于阈值的可靠知识库依据。",
            "answer": build_no_evidence_answer(question),
            "sources": [],
        }

    local_retrieval = any(item.get("retrieval_mode") == "local_keyword" for item in reliable_results)
    try:
        answer = _call_llm(question, reliable_results)
        offline_generation = False
    except Exception:
        if not settings.offline_fallback_enabled:
            raise
        answer = build_offline_extract_answer(question, reliable_results)
        offline_generation = True

    message = (
        "外部模型或向量服务不可用，已使用本地离线演示模式。"
        if local_retrieval or offline_generation
        else "已基于知识库检索结果生成回答。"
    )
    return {
        "message": message,
        "answer": answer,
        "sources": build_sources(reliable_results),
    }
