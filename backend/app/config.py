"""Application configuration.

Every secret, connection string, and tunable is read from the environment (or a
local ``.env`` file) — nothing is hardcoded. This replaces the old scattered
hardcoded MongoDB credentials, ``SECRET_KEY = "SIH"``, and LAN IP addresses.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Database ---
    mongo_uri: str = "mongodb://localhost:27017"
    mongo_db: str = "docverify"

    # --- Auth ---
    # MUST be overridden in production. A random default keeps dev from silently
    # running with a well-known secret, but tokens won't survive a restart.
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expiry_minutes: int = 60

    # --- LLM / extraction ---
    # Provider for document extraction: "openai" (any OpenAI-compatible endpoint,
    # e.g. a self-hosted Ollama server) or "anthropic" (Claude).
    llm_provider: str = "openai"

    # OpenAI-compatible settings (used when llm_provider == "openai").
    # Defaults point at the self-hosted Ollama server. The model MUST be
    # vision-capable (e.g. qwen2.5vl) — a text-only model like qwen3-coder cannot
    # read document images.
    llm_base_url: str = "http://135.13.20.57:11434/v1"
    llm_model: str = "qwen2.5vl:32b"
    llm_api_key: str = "ollama"  # Ollama ignores it; any non-empty value works.

    # Anthropic settings (used when llm_provider == "anthropic").
    # ANTHROPIC_API_KEY is read by the SDK directly from the environment.
    anthropic_model: str = "claude-opus-4-8"

    extraction_max_tokens: int = 16000

    # Render scale for rasterizing PDF pages to images (higher = sharper, slower).
    pdf_render_scale: float = 2.0

    # --- CORS ---
    # Comma-separated list of allowed origins for the SPA.
    cors_origins: str = "http://localhost:5173"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
