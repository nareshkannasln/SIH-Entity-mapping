"""Document extraction using a vision LLM + structured (JSON-schema) outputs.

A single vision call does OCR *and* extraction — no separate OCR service. Two
backends are supported and selected via ``settings.llm_provider``:

- ``openai``    — any OpenAI-compatible endpoint (default: a self-hosted Ollama
                  server running a vision model such as ``qwen2.5vl``).
- ``anthropic`` — Claude via the Anthropic SDK.

Input handling is unified: images are used as-is and PDFs are rasterized to page
images with ``pypdfium2`` (a pip wheel — no system poppler needed), so both
backends receive image content. The model returns validated JSON built at runtime
from the doc type's field schema — no ``eval``, no positional arrays.
"""

import base64
import json
import logging
from io import BytesIO
from typing import Any

from fastapi import HTTPException, status

from .config import get_settings
from .models import DocType

logger = logging.getLogger(__name__)

_SUPPORTED_IMAGE_TYPES = {"image/png", "image/jpeg", "image/webp", "image/gif"}

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

# Lazily-constructed clients (so importing this module needs no credentials).
_openai_client = None
_anthropic_client = None


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


def _rasterize_pdf(pdf_bytes: bytes) -> list[bytes]:
    """Render each PDF page to PNG bytes using pypdfium2 (no system poppler)."""
    import pypdfium2 as pdfium

    scale = get_settings().pdf_render_scale
    pdf = pdfium.PdfDocument(pdf_bytes)
    try:
        pages: list[bytes] = []
        for page in pdf:
            bitmap = page.render(scale=scale)
            image = bitmap.to_pil()
            buf = BytesIO()
            image.save(buf, format="PNG")
            pages.append(buf.getvalue())
            bitmap.close()
            page.close()
        return pages
    finally:
        pdf.close()


def _to_images(file_bytes: bytes, content_type: str) -> list[tuple[bytes, str]]:
    """Return a list of (image_bytes, media_type) for the uploaded document."""
    if content_type == "application/pdf":
        pages = _rasterize_pdf(file_bytes)
        if not pages:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "PDF has no pages")
        return [(p, "image/png") for p in pages]
    if content_type in _SUPPORTED_IMAGE_TYPES:
        return [(file_bytes, content_type)]
    raise HTTPException(
        status.HTTP_400_BAD_REQUEST,
        f"Unsupported file type '{content_type}'. Allowed: PDF, PNG, JPEG, WEBP, GIF.",
    )


def _prompt(doc_type: DocType) -> str:
    field_list = ", ".join(f"{f.name} ({f.type})" for f in doc_type.fields)
    return (
        f"Target document type: {doc_type.label} (key: {doc_type.key}).\n"
        f"Extract these fields: {field_list}."
    )


def _parse_json(text: str | None) -> dict[str, Any]:
    if not text:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Empty extraction result")
    # Be tolerant of code fences some models emit despite instructions.
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        cleaned = cleaned[cleaned.find("{") : cleaned.rfind("}") + 1]
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as exc:
        logger.error("Model returned non-JSON: %s", text[:500])
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Malformed extraction result") from exc


# --- OpenAI-compatible backend (Ollama, etc.) ---
def _get_openai_client():
    global _openai_client
    if _openai_client is None:
        from openai import AsyncOpenAI

        settings = get_settings()
        _openai_client = AsyncOpenAI(base_url=settings.llm_base_url, api_key=settings.llm_api_key)
    return _openai_client


async def _extract_openai(
    images: list[tuple[bytes, str]], schema: dict[str, Any], prompt: str
) -> dict[str, Any]:
    settings = get_settings()
    content: list[dict[str, Any]] = [{"type": "text", "text": prompt}]
    for img_bytes, media_type in images:
        data = base64.standard_b64encode(img_bytes).decode("utf-8")
        content.append(
            {"type": "image_url", "image_url": {"url": f"data:{media_type};base64,{data}"}}
        )

    try:
        resp = await _get_openai_client().chat.completions.create(
            model=settings.llm_model,
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
def _get_anthropic_client():
    global _anthropic_client
    if _anthropic_client is None:
        from anthropic import AsyncAnthropic

        _anthropic_client = AsyncAnthropic()
    return _anthropic_client


async def _extract_anthropic(
    images: list[tuple[bytes, str]], schema: dict[str, Any], prompt: str
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
        async with _get_anthropic_client().messages.stream(
            model=settings.anthropic_model,
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


async def extract(file_bytes: bytes, content_type: str, doc_type: DocType) -> dict[str, Any]:
    """Extract structured fields from a document using the configured provider."""
    images = _to_images(file_bytes, content_type)
    schema = build_json_schema(doc_type)
    prompt = _prompt(doc_type)

    if get_settings().llm_provider == "anthropic":
        return await _extract_anthropic(images, schema, prompt)
    return await _extract_openai(images, schema, prompt)
