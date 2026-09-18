import re
from functools import lru_cache
from pathlib import Path

from app.rag.loaders import load_document
from app.rag.splitter import split_documents


STOP_BIGRAMS = {
    "什么",
    "怎么",
    "如何",
    "应该",
    "哪些",
    "一下",
    "出现",
    "进行",
}


def _tokens(text: str) -> set[str]:
    """Build lightweight tokens for an offline Chinese/English demo search."""
    normalized = str(text).lower().replace("_", "-")
    tokens = set(re.findall(r"[a-z0-9]+(?:-[a-z0-9]+)*", normalized))
    for segment in re.findall(r"[\u4e00-\u9fff]+", normalized):
        for index in range(len(segment) - 1):
            bigram = segment[index : index + 2]
            if bigram not in STOP_BIGRAMS:
                tokens.add(bigram)
    return tokens


def _score(query: str, content: str) -> float:
    query_tokens = _tokens(query)
    if not query_tokens:
        return 0.0
    content_tokens = _tokens(content)
    overlap = query_tokens & content_tokens
    coverage = len(overlap) / len(query_tokens)

    exact_codes = {
        token
        for token in query_tokens
        if any(char.isdigit() for char in token) and token in content.lower().replace("_", "-")
    }
    code_bonus = min(len(exact_codes) * 0.12, 0.24)
    return min(1.0, coverage + code_bonus)


@lru_cache(maxsize=8)
def _load_chunks(sample_docs_dir: str) -> tuple:
    chunks = []
    root = Path(sample_docs_dir)
    for path in sorted(root.glob("*")):
        if path.suffix.lower() not in {".txt", ".pdf", ".docx"}:
            continue
        for chunk in split_documents(load_document(path, file_name=path.name)):
            chunks.append((chunk.page_content, dict(chunk.metadata)))
    return tuple(chunks)


def search_sample_documents_locally(query: str, top_k: int = 4) -> list[dict]:
    """Search bundled demo documents without an external embedding service."""
    from app.core.config import get_settings

    settings = get_settings()
    ranked = []
    for content, metadata in _load_chunks(str(settings.sample_docs_dir.resolve())):
        score = _score(query, content)
        if score <= 0:
            continue
        ranked.append(
            {
                "content": content,
                "metadata": metadata,
                "similarity_score": round(score, 6),
                "retrieval_mode": "local_keyword",
            }
        )
    ranked.sort(key=lambda item: item["similarity_score"], reverse=True)
    return ranked[: max(int(top_k), 1)]
