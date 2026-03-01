"""Application configuration from environment."""
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # API
    api_title: str = "DepthOfInk"
    api_version: str = "0.1.0"

    # Paths (relative to backend root or absolute)
    data_dir: Path = Path("data")
    uploads_dir: Path = Path("data/uploads")
    chroma_dir: Path = Path("data/chroma")

    # LLM provider: "openai" | "bedrock"
    # "openai" also works for Ollama and any OpenAI-compatible API
    llm_provider: str = "openai"

    # OpenAI / OpenAI-compatible settings
    openai_api_key: str = ""
    openai_base_url: str | None = None

    # AWS Bedrock settings (used when llm_provider=bedrock)
    aws_region: str = "us-east-1"

    # Model names (provider-specific)
    # OpenAI defaults: gpt-4o-mini / text-embedding-3-small
    # Bedrock examples: us.anthropic.claude-3-5-haiku-20241022-v1:0 / amazon.titan-embed-text-v2:0
    embedding_model: str = "text-embedding-3-small"
    chat_model: str = "gpt-4o-mini"

    # RAG
    chunk_size: int = 800
    chunk_overlap: int = 150
    top_k_retrieve: int = 5
    min_relevance_score: float = 0.0

    # Reranking
    rerank_enabled: bool = True
    rerank_initial_k: int = 15
    rerank_final_k: int = 5

    # Character extraction
    max_characters: int = 20
    chars_per_sample: int = 12000

    # CORS (comma-separated origins for production, e.g. "https://myapp.example.com")
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    # Upload limits
    max_upload_size_mb: int = 50

    # Chat input limits
    max_message_length: int = 5000

    # Logging: "json" for production structured logs, "text" for dev
    log_format: str = "text"
    log_level: str = "INFO"

    # Rate limiting (set RATE_LIMIT_ENABLED=false to disable in dev)
    rate_limit_enabled: bool = True
    rate_limit_default: str = "60/minute"
    rate_limit_upload: str = "5/hour"
    rate_limit_chat: str = "30/minute"

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.data_dir = self.data_dir.resolve()
        self.uploads_dir = self.uploads_dir.resolve()
        self.chroma_dir = self.chroma_dir.resolve()


settings = Settings()
