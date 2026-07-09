from pathlib import Path
from typing import Optional

from app.rag.loaders import load_document
from app.rag.splitter import split_documents
from app.rag.vector_store import add_documents_to_store


def ingest_file(path: Path, file_name: Optional[str] = None) -> int:
    """Parse, split, embed, and persist one document into Chroma."""
    documents = load_document(path, file_name=file_name)
    chunks = split_documents(documents)
    return add_documents_to_store(chunks)
