def _validate_api_key(api_key: str, env_name: str) -> str:
    if not api_key or not api_key.strip():
        raise RuntimeError(f"请先在 .env 中配置 {env_name}。")
    return api_key.strip()


def build_chat_kwargs(settings) -> dict:
    kwargs = {
        "model": settings.chat_model,
        "temperature": 0.2,
        "api_key": _validate_api_key(settings.chat_api_key, "CHAT_API_KEY"),
    }
    if settings.chat_base_url:
        kwargs["base_url"] = settings.chat_base_url
    return kwargs


def build_embedding_kwargs(settings) -> dict:
    kwargs = {
        "model": settings.embedding_model,
        "api_key": _validate_api_key(settings.embedding_api_key, "EMBEDDING_API_KEY"),
    }
    if settings.embedding_base_url:
        kwargs["base_url"] = settings.embedding_base_url
    kwargs["check_embedding_ctx_length"] = False
    return kwargs

def get_chat_model():
    """Create the chat model lazily so health checks can run without an API key."""
    from langchain_openai import ChatOpenAI
    from app.core.config import get_settings

    return ChatOpenAI(**build_chat_kwargs(get_settings()))


def get_embedding_model():
    """Create embeddings lazily because upload and ingest are the only callers."""
    from langchain_openai import OpenAIEmbeddings
    from app.core.config import get_settings

    return OpenAIEmbeddings(**build_embedding_kwargs(get_settings()))
