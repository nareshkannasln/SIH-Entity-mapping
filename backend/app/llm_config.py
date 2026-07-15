"""Effective LLM configuration = admin's DB overrides layered over ``.env``.

The admin Settings page writes a single document (``_id == "llm"``) into the
``app_settings`` collection. Anything it doesn't set falls back to the
provider's ``.env`` defaults, so the app still runs with no DB config at all.
"""

import os
from dataclasses import dataclass

from . import db
from .config import Settings, get_settings

_SETTINGS_ID = "llm"


@dataclass
class LLMConfig:
    provider: str
    model: str
    base_url: str
    api_key: str


def _default_model(settings: Settings, provider: str) -> str:
    return {
        "openai": settings.llm_model,
        "gemini": settings.gemini_model,
        "groq": settings.groq_model,
        "openrouter": settings.openrouter_model,
        "anthropic": settings.anthropic_model,
        "offline": "tesseract+ner",
    }.get(provider, settings.llm_model)


def _default_base_url(settings: Settings, provider: str) -> str:
    return {
        "openai": settings.llm_base_url,
        "gemini": settings.gemini_base_url,
        "groq": settings.groq_base_url,
        "openrouter": settings.openrouter_base_url,
        "anthropic": "",
        "offline": "",
    }.get(provider, settings.llm_base_url)


def _default_api_key(settings: Settings, provider: str) -> str:
    return {
        "openai": settings.llm_api_key,
        "gemini": settings.gemini_api_key,
        "groq": settings.groq_api_key,
        "openrouter": settings.openrouter_api_key,
        # The Anthropic SDK normally reads this from the environment.
        "anthropic": os.environ.get("ANTHROPIC_API_KEY", ""),
        # The offline engine needs no key.
        "offline": "",
    }.get(provider, settings.llm_api_key)


def _resolve(settings: Settings, doc: dict | None) -> LLMConfig:
    doc = doc or {}
    provider = doc.get("provider") or settings.llm_provider
    return LLMConfig(
        provider=provider,
        model=doc.get("model") or _default_model(settings, provider),
        base_url=doc.get("base_url") or _default_base_url(settings, provider),
        api_key=doc.get("api_key") or _default_api_key(settings, provider),
    )


async def get_llm_config() -> LLMConfig:
    """Resolve the active LLM config (DB overrides win over env defaults)."""
    doc = await db.app_settings().find_one({"_id": _SETTINGS_ID})
    return _resolve(get_settings(), doc)


async def get_stored_settings_doc() -> dict | None:
    """Raw stored settings doc (or None) — for the admin Settings endpoint."""
    return await db.app_settings().find_one({"_id": _SETTINGS_ID})


async def save_settings(provider: str, model: str, base_url: str, api_key: str | None) -> None:
    """Upsert the LLM settings doc. ``api_key=None`` keeps the existing key."""
    update = {"provider": provider, "model": model, "base_url": base_url}
    if api_key:
        update["api_key"] = api_key
    await db.app_settings().update_one(
        {"_id": _SETTINGS_ID}, {"$set": update}, upsert=True
    )
