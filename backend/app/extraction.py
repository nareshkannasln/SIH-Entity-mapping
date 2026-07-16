"""Document extraction using a vision LLM + structured (JSON-schema) outputs.

A single vision call does OCR *and* extraction — no separate OCR service. Three
backends are supported, selected via the effective provider (see
``llm_config.get_llm_config`` — an admin's DB settings layered over ``.env``):

- ``openai``    — any OpenAI-compatible endpoint (default: a self-hosted Ollama
                  server running a vision model such as ``qwen2.5vl``).
- ``gemini``    — Google Gemini via its OpenAI-compatible endpoint (reuses the
                  ``openai`` code path).
- ``anthropic`` — Claude via the Anthropic SDK.

Input handling is unified: images are used as-is and PDFs are rasterized to page
images with ``pypdfium2`` (a pip wheel — no system poppler needed), so both
backends receive image content. The model returns validated JSON built at runtime
from the doc type's field schema — no ``eval``, no positional arrays.
"""

import base64
import json
import logging
import re
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

from fastapi import HTTPException, status

from .config import get_settings
from .images import to_images
from .llm_config import get_llm_config
from .models import DocType

logger = logging.getLogger(__name__)


@dataclass
class ExtractionResult:
    """The extracted fields plus a human-readable label of the engine used."""

    data: dict[str, Any]
    engine: str
    # Raw OCR text, when the engine produces it (offline engine only).
    raw_text: str | None = None

_SYSTEM_PROMPT = (
    "You are a meticulous document data-extraction engine. You are given one or "
    "more page images of a document and a target schema. Read the document and "
    "extract each field's value accurately.\n"
    "- If a field is not present in the document, return null (or an empty string).\n"
    "- If the document is in a non-English language, translate extracted text "
    "values to English.\n"
    "- Also classify what kind of document this actually is, as the "
    "'document_type' field, using the provided document type key when it matches.\n"
    "Return only the structured JSON requested — no prose, no code fences."
)

_JSON_TYPE = {
    "string": "string",
    "date": "string",
    "integer": "integer",
    "number": "number",
    "boolean": "boolean",
}

# Clients are cached by connection identity so a runtime settings change (new
# base URL or key) transparently builds a fresh client on next use.
_openai_clients: dict[tuple[str, str], Any] = {}
_anthropic_clients: dict[str, Any] = {}


def build_json_schema(doc_type: DocType) -> dict[str, Any]:
    """Build a JSON schema for structured output from a doc type's fields.

    Always includes a ``document_type`` field so a document/type mismatch can be
    detected safely.
    """
    properties: dict[str, Any] = {
        "document_type": {
            "type": "string",
            "description": "The kind of document this actually is.",
        }
    }
    required = ["document_type"]
    for f in doc_type.fields:
        json_type = _JSON_TYPE.get(f.type, "string")
        properties[f.name] = {
            "type": [json_type, "null"],
            "description": f.description or f.name,
        }
        required.append(f.name)

    return {
        "type": "object",
        "properties": properties,
        "required": required,
        "additionalProperties": False,
    }


def _prompt(doc_type: DocType) -> str:
    field_list = ", ".join(f"{f.name} ({f.type})" for f in doc_type.fields)
    return (
        f"Target document type: {doc_type.label} (key: {doc_type.key}).\n"
        f"Extract these fields: {field_list}."
    )


_FENCE_RE = re.compile(r"\A```[A-Za-z0-9_-]*[ \t]*\r?\n?|\r?\n?```\Z")


def _json_candidates(text: str) -> Iterator[str]:
    """Yield progressively more forgiving readings of a model's JSON reply.

    Structured outputs are supposed to make this unnecessary, but real endpoints
    still bend the contract, and the payload is usually valid apart from its
    wrapper — worth repairing rather than discarding.
    """
    s = text.strip()

    # 1. As-is (with any markdown fence removed).
    if s.startswith("```"):
        s = _FENCE_RE.sub("", s).strip()
    yield s

    # 2. The widest brace-delimited span, for prose on either side.
    i, j = s.find("{"), s.rfind("}")
    if i != -1 and j > i:
        yield s[i : j + 1]

    # 3. A body whose opening brace is missing. NVIDIA's DiffusionGemma does this
    #    under response_format=json_schema: the reply is a complete object except
    #    it starts at the first key. Restore the brace rather than lose the data.
    if not s.startswith("{") and s.endswith("}"):
        yield "{" + s


def _parse_json(text: str | None) -> dict[str, Any]:
    if not text:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Empty extraction result")

    for candidate in _json_candidates(text):
        try:
            data = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict):
            return data

    logger.error("Model returned non-JSON: %s", text[:500])
    raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Malformed extraction result")


# --- OpenAI-compatible backend (Ollama, Gemini, etc.) ---
def _get_openai_client(base_url: str, api_key: str):
    key = (base_url, api_key)
    if key not in _openai_clients:
        from openai import AsyncOpenAI

        _openai_clients[key] = AsyncOpenAI(base_url=base_url, api_key=api_key)
    return _openai_clients[key]


async def _extract_openai(
    images: list[tuple[bytes, str]], schema: dict[str, Any], prompt: str, *, client, model: str
) -> dict[str, Any]:
    settings = get_settings()
    content: list[dict[str, Any]] = [{"type": "text", "text": prompt}]
    for img_bytes, media_type in images:
        data = base64.standard_b64encode(img_bytes).decode("utf-8")
        content.append(
            {"type": "image_url", "image_url": {"url": f"data:{media_type};base64,{data}"}}
        )

    try:
        resp = await client.chat.completions.create(
            model=model,
            max_tokens=settings.extraction_max_tokens,
            temperature=0,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": content},
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {"name": "extraction", "schema": schema, "strict": True},
            },
        )
    except Exception as exc:
        logger.exception("OpenAI-compatible extraction call failed")
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY, "Document extraction service failed"
        ) from exc

    return _parse_json(resp.choices[0].message.content)


# --- Anthropic backend (Claude) ---
def _get_anthropic_client(api_key: str):
    if api_key not in _anthropic_clients:
        from anthropic import AsyncAnthropic

        # api_key="" -> let the SDK read ANTHROPIC_API_KEY from the environment.
        _anthropic_clients[api_key] = AsyncAnthropic(api_key=api_key or None)
    return _anthropic_clients[api_key]


async def _extract_anthropic(
    images: list[tuple[bytes, str]], schema: dict[str, Any], prompt: str, *, client, model: str
) -> dict[str, Any]:
    settings = get_settings()
    content: list[dict[str, Any]] = []
    for img_bytes, media_type in images:
        data = base64.standard_b64encode(img_bytes).decode("utf-8")
        content.append(
            {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": data}}
        )
    content.append({"type": "text", "text": prompt})

    try:
        async with client.messages.stream(
            model=model,
            max_tokens=settings.extraction_max_tokens,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": content}],
            output_config={"format": {"type": "json_schema", "schema": schema}},
        ) as stream:
            message = await stream.get_final_message()
    except Exception as exc:
        logger.exception("Anthropic extraction call failed")
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY, "Document extraction service failed"
        ) from exc

    if message.stop_reason == "refusal":
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "The document could not be processed (content declined).",
        )
    text = next((b.text for b in message.content if b.type == "text"), None)
    return _parse_json(text)


async def extract(file_bytes: bytes, content_type: str, doc_type: DocType) -> ExtractionResult:
    """Extract structured fields from a document using the configured provider.

    Returns the extracted field dict plus an ``engine`` label describing which
    backend produced it (surfaced in the UI).
    """
    cfg = await get_llm_config()

    # Offline engine: local Tesseract OCR + NER, no API and no page-image payload
    # to a remote model.
    if cfg.provider == "offline":
        from .offline_extraction import offline_extract

        data, text = offline_extract(file_bytes, content_type, doc_type)
        return ExtractionResult(data=data, engine="Offline OCR + NER", raw_text=text)

    images = to_images(file_bytes, content_type)
    schema = build_json_schema(doc_type)
    prompt = _prompt(doc_type)

    if cfg.provider == "anthropic":
        data = await _extract_anthropic(
            images, schema, prompt, client=_get_anthropic_client(cfg.api_key), model=cfg.model
        )
        return ExtractionResult(data=data, engine=f"Anthropic · {cfg.model}")

    # "openai", "gemini", "groq", "openrouter" and "nvidia" all expose an
    # OpenAI-compatible endpoint, so they share this path.
    if not cfg.api_key:
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            f"No API key is configured for LLM provider '{cfg.provider}'. "
            "Set one on the Settings page, or switch to the offline engine.",
        )
    client = _get_openai_client(cfg.base_url, cfg.api_key)
    data = await _extract_openai(images, schema, prompt, client=client, model=cfg.model)
    return ExtractionResult(data=data, engine=f"{cfg.provider} · {cfg.model}")
