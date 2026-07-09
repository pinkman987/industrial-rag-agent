from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.core.config import get_settings
from app.rag.ingest import ingest_file


def main() -> None:
    settings = get_settings()
    supported_suffixes = {".pdf", ".txt", ".docx"}
    files = [
        path
        for path in sorted(settings.sample_docs_dir.iterdir())
        if path.is_file() and path.suffix.lower() in supported_suffixes
    ]

    if not files:
        print(f"未找到样例文档：{settings.sample_docs_dir}")
        return

    total_chunks = 0
    for path in files:
        chunk_count = ingest_file(path, file_name=path.name)
        total_chunks += chunk_count
        print(f"已入库：{path.name}，chunk_count={chunk_count}")

    print(f"样例文档入库完成，文件数={len(files)}，总chunk数={total_chunks}")


if __name__ == "__main__":
    main()
