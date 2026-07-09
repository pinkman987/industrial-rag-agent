from pathlib import Path
import shutil

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.core.config import get_settings
from app.rag.ingest import ingest_file
from app.rag.loaders import UnsupportedFileTypeError
from app.schemas.rag import UploadResponse


router = APIRouter(prefix="/api/documents", tags=["documents"])

SUPPORTED_SUFFIXES = {".pdf", ".txt", ".docx"}


@router.post("/upload", response_model=UploadResponse)
def upload_document(file: UploadFile = File(...)):
    settings = get_settings()
    original_name = file.filename or "uploaded_document"
    suffix = Path(original_name).suffix.lower()
    if suffix not in SUPPORTED_SUFFIXES:
        raise HTTPException(status_code=400, detail="仅支持上传 .pdf、.txt、.docx 文件。")

    save_path = settings.upload_dir / original_name
    try:
        with save_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        chunk_count = ingest_file(save_path, file_name=original_name)
    except UnsupportedFileTypeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return UploadResponse(
        message="文档已解析、切块并写入 Chroma。",
        file_name=original_name,
        chunk_count=chunk_count,
    )
