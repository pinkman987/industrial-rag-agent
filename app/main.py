from fastapi import FastAPI

from app.api import chat, devices, diagnosis, documents, tool_chat
from app.core.config import get_settings


app = FastAPI(
    title="工业设备运维知识库RAG系统",
    description="阶段一：文档上传、向量化、知识库检索和带引用问答。",
    version="0.1.0",
)

app.include_router(documents.router)
app.include_router(chat.router)
app.include_router(tool_chat.router)
app.include_router(diagnosis.router)
app.include_router(devices.router)


@app.get("/health")
def health_check():
    settings = get_settings()
    return {
        "message": "服务运行正常。",
        "status": "ok",
        "chroma_persist_dir": str(settings.chroma_persist_dir),
        "upload_dir": str(settings.upload_dir),
        "top_k": settings.top_k,
        "similarity_threshold": settings.similarity_threshold,
    }
