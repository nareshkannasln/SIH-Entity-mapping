"""Document extraction using Claude vision + structured outputs.

This single module replaces the old three-service pipeline (Surya OCR + Ollama
``gemma2:9b`` + poppler/pdf2image). Claude reads PDFs and images natively and
returns validated JSON via ``output_config.format`` — so there is no OCR step, no
GPU, no ``eval()`` of model output, and no brittle positional-array contract.
"""

import base64
import logging
from typing import Any

from anthropic import AsyncAnthropic
from fastapi import HTTPException, status

from .config import get_settings
from .models import DocType, SchemaField

logger = logging.getLogger(__name__)

# The SDK reads ANTHROPIC_API_KEY from the environment; no key is hardcoded.
# Constructed lazily so importing this module (e.g. in tests) doesn't require a key.
_client: AsyncAnthropic | None = None


def get_client() -> AsyncAnthropic:
    global _client
    if _client is None:
        _client = AsyncAnthropic()
    return _client

_SUPPORTED_IMAGE_TYPES = {"image/png", "image/jpeg", "image/webp", "image/gif"}

_SYSTEM_PROMPT = (
    "You are a meticulous document data-extraction engine. You are given a "
    "scanned document (image or PDF) and a target schema. Read the document and "
    "extract each field's value accurately.\n"
    "- If a field is not present in the document, return an empty string (or null).\n"
    "- If the document is in a non-English language, translate extracted text "
    "values to English.\n"
    "- Also classify what kind of document this actually is, as the "
    "'document_type' field, using the provided document type key when it matches.\n"
    "Return only the structured data requested."
)

# Map our field types to JSON-schema types (all nullable so missing values are allowed).
_JSON_TYPE = {
    "string": "string",
    "date": "string",
    "integer": "integer",
    "number": "number",
    "boolean": "boolean",
}


def build_json_schema(doc_type: DocType) -> dict[str, Any]:
    """Build a JSON schema for structured output from a doc type's fields.

    Always includes a ``document_type`` field so a document/type mismatch can be
    detected safely (this preserves the old positional index-0 doc-type check).
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
        # Allow null so the model can signal a missing field without breaking the schema.
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


def _content_block(file_bytes: bytes, content_type: str) -> dict[str, Any]:
    data = base64.standard_b64encode(file_bytes).decode("utf-8")
    if content_type == "application/pdf":
        return {
            "type": "document",
            "source": {"type": "base64", "media_type": "application/pdf", "data": data},
        }
    if content_type in _SUPPORTED_IMAGE_TYPES:
        return {
            "type": "image",
            "source": {"type": "base64", "media_type": content_type, "data": data},
        }
    raise HTTPException(
        status.HTTP_400_BAD_REQUEST,
        f"Unsupported file type '{content_type}'. Allowed: PDF, PNG, JPEG, WEBP, GIF.",
    )


async def extract(file_bytes: bytes, content_type: str, doc_type: DocType) -> dict[str, Any]:
    """Run extraction and return a dict keyed by field name (+ 'document_type')."""
    import json

    settings = get_settings()
    schema = build_json_schema(doc_type)

    field_list = ", ".join(f"{f.name} ({f.type})" for f in doc_type.fields)
    prompt = (
        f"Target document type: {doc_type.label} (key: {doc_type.key}).\n"
        f"Extract these fields: {field_list}."
    )

    content = [_content_block(file_bytes, content_type), {"type": "text", "text": prompt}]

    try:
        async with get_client().messages.stream(
            model=settings.anthropic_model,
            max_tokens=settings.extraction_max_tokens,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": content}],
            output_config={"format": {"type": "json_schema", "schema": schema}},
        ) as stream:
            message = await stream.get_final_message()
    except Exception as exc:  # anthropic.APIError and friends
        logger.exception("Extraction call failed")
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY, "Document extraction service failed"
        ) from exc

    if message.stop_reason == "refusal":
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "The document could not be processed (content declined).",
        )

    text = next((b.text for b in message.content if b.type == "text"), None)
    if not text:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Empty extraction result")

    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        logger.error("Model returned non-JSON despite structured output: %s", text[:500])
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Malformed extraction result") from exc
