import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EMBEDDING_BASE_URL = "https://open.bigmodel.cn/api/paas/v4"
DEFAULT_EMBEDDING_MODEL = "embedding-3"
TEST_INPUT = "自然语言处理技术发展史"


def build_client():
    from dotenv import load_dotenv
    from openai import OpenAI

    load_dotenv(PROJECT_ROOT / ".env")

    api_key = os.getenv("EMBEDDING_API_KEY", "").strip()
    base_url = os.getenv("EMBEDDING_BASE_URL", "").strip() or DEFAULT_EMBEDDING_BASE_URL
    model = os.getenv("EMBEDDING_MODEL", "").strip() or DEFAULT_EMBEDDING_MODEL

    print(f"embedding_base_url: {base_url}")
    print(f"embedding_model: {model}")
    if not api_key:
        raise ValueError("EMBEDDING_API_KEY is empty. Please configure it in .env first.")

    return OpenAI(api_key=api_key, base_url=base_url), model


def main() -> None:
    try:
        client, model = build_client()
        response = client.embeddings.create(input=TEST_INPUT, model=model)
        embedding = response.data[0].embedding
        print(f"Success. Embedding dimension: {len(embedding)}")
    except Exception as exc:
        print(f"Failed. Error type: {type(exc).__name__}")
        print(f"Error message: {exc}")


if __name__ == "__main__":
    main()
