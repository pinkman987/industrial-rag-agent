from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "工业设备运维知识库RAG系统"
    chat_api_key: str = ""
    chat_base_url: str = "https://api.deepseek.com"
    chat_model: str = "deepseek-v4-flash"
    embedding_api_key: str = ""
    embedding_base_url: str = "https://open.bigmodel.cn/api/paas/v4"
    embedding_model: str = "embedding-3"

    chroma_persist_dir: Path = Path("data/chroma")
    upload_dir: Path = Path("data/uploads")
    sample_docs_dir: Path = Path("data/sample_docs")

    similarity_threshold: float = 0.35
    offline_similarity_threshold: float = 0.18
    offline_fallback_enabled: bool = True
    chunk_size: int = 700
    chunk_overlap: int = 100
    top_k: int = 4

    mysql_host: str = "127.0.0.1"
    mysql_port: int = 3306
    mysql_user: str = "rag_user"
    mysql_password: str = "rag_password"
    mysql_database: str = "industrial_rag"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def mysql_url(self) -> str:
        return (
            f"mysql+pymysql://{self.mysql_user}:{self.mysql_password}"
            f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}?charset=utf8mb4"
        )


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.chroma_persist_dir.mkdir(parents=True, exist_ok=True)
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    settings.sample_docs_dir.mkdir(parents=True, exist_ok=True)
    return settings
