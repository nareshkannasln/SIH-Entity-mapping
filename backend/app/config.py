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

    # --- Bootstrap admin (seeded on first startup if missing) ---
    admin_username: str = "admin@docverify"
    admin_email: str = "admin@docverify.com"
    admin_password: str = "admin@123"

    # --- LLM / extraction ---
    # Provider for document extraction:
    #   "openai"     — any OpenAI-compatible endpoint (e.g. a self-hosted Ollama server)
    #   "anthropic"  — Claude
    #   "gemini"     — Google Gemini (generous free tier, OpenAI-compatible endpoint)
    #   "groq"       — Groq (free tier, very fast, OpenAI-compatible endpoint)
    #   "openrouter" — OpenRouter free models (OpenAI-compatible endpoint)
    #   "offline"    — the built-in Tesseract OCR + NER engine (no API, no GPU)
    llm_provider: str = "offline"

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

    # Gemini settings (used when llm_provider == "gemini"). Gemini exposes an
    # OpenAI-compatible endpoint, so extraction reuses the OpenAI code path.
    # The model MUST be vision-capable (gemini-2.5-flash, gemini-2.5-pro, ...).
    gemini_base_url: str = "https://generativelanguage.googleapis.com/v1beta/openai/"
    gemini_model: str = "gemini-2.5-flash"
    gemini_api_key: str = ""

    # Groq settings (used when llm_provider == "groq"). Free tier, OpenAI-compatible,
    # extremely fast. The model MUST be vision-capable (e.g. a Llama Vision model).
    groq_base_url: str = "https://api.groq.com/openai/v1"
    groq_model: str = "meta-llama/llama-4-scout-17b-16e-instruct"
    groq_api_key: str = ""

    # OpenRouter settings (used when llm_provider == "openrouter"). Routes to many
    # community-hosted models, several at $0/M tokens. The model MUST be
    # vision-capable; ":free" variants are rate-limited but cost nothing.
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_model: str = "meta-llama/llama-3.2-11b-vision-instruct:free"
    openrouter_api_key: str = ""

    # NVIDIA settings (used when llm_provider == "nvidia"). build.nvidia.com hosts
    # many models on a free evaluation tier behind an OpenAI-compatible endpoint,
    # so extraction reuses the OpenAI code path. The model MUST be vision-capable
    # — DiffusionGemma is multimodal and handles OCR / document understanding.
    nvidia_base_url: str = "https://integrate.api.nvidia.com/v1"
    nvidia_model: str = "google/diffusiongemma-26b-a4b-it"
    nvidia_api_key: str = ""

    extraction_max_tokens: int = 16000

    # --- Offline OCR + NER engine (used when llm_provider == "offline") ---
    # OCR engine backing the offline provider:
    #   "tesseract" — system binary; tiny footprint, weakest on noisy scans.
    #   "surya"     — Surya OCR 2 (GGUF) served by llama.cpp; CPU-only, far more
    #                 accurate, but pulls ~2GB of weights on first use.
    ocr_engine: str = "tesseract"
    # Tesseract language(s) for OCR, e.g. "eng" or "eng+hin".
    ocr_languages: str = "eng"
    # spaCy model for named-entity recognition. If it isn't installed the engine
    # degrades gracefully to its regex + label-matching rules.
    spacy_model: str = "en_core_web_sm"

    # --- Surya (ocr_engine == "surya") ---
    # Surya reads these from the process environment, so the OCR entry point
    # exports them before importing surya. "cpu" keeps inference GPU-free;
    # llama.cpp picks the best CPU kernel for the host at runtime.
    torch_device: str = "cpu"
    # Absolute path to the llama-server binary. Empty = resolve it from PATH.
    llama_cpp_binary: str = ""

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
