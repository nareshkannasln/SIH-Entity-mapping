"""Admin-only runtime LLM configuration endpoints."""

from fastapi import APIRouter, Depends

from ..llm_config import get_llm_config, save_settings
from ..models import LLMSettingsIn, LLMSettingsPublic
from ..security import get_current_admin

router = APIRouter(prefix="/api/settings", tags=["settings"])


async def _current_public() -> LLMSettingsPublic:
    cfg = await get_llm_config()
    return LLMSettingsPublic(
        provider=cfg.provider,
        model=cfg.model,
        base_url=cfg.base_url,
        api_key_set=bool(cfg.api_key),
    )


@router.get("", response_model=LLMSettingsPublic)
async def read_settings(_: str = Depends(get_current_admin)):
    return await _current_public()


@router.put("", response_model=LLMSettingsPublic)
async def update_settings(payload: LLMSettingsIn, _: str = Depends(get_current_admin)):
    # An empty api_key means "keep the existing key".
    await save_settings(
        payload.provider, payload.model, payload.base_url, payload.api_key or None
    )
    return await _current_public()
