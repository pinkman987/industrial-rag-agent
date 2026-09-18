"""Command-line diagnostic search for the industrial RAG project."""

import argparse
import json

from app.rag.vector_store import search_knowledge_base


def main() -> None:
    parser = argparse.ArgumentParser(description="测试工业设备知识库检索")
    parser.add_argument("query", help="要检索的设备故障问题")
    parser.add_argument("--top-k", type=int, default=4, help="最多返回的文本块数量")
    args = parser.parse_args()

    results = search_knowledge_base(args.query, top_k=args.top_k)
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
