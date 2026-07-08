"""Tests for the extraction input handling and the OpenAI-compatible backend.

No network/LLM is called — the client is mocked and images are generated locally.
"""

import asyncio
import json
from io import BytesIO
from types import SimpleNamespace

import pytest
from PIL import Image

from app import extraction
from app.models import DocType, SchemaField


def _doc_type() -> DocType:
    return DocType(
        key="marksheet",
        label="Marksheet",
        fields=[SchemaField(name="name"), SchemaField(name="roll_number", type="integer")],
    )


def _png_bytes() -> bytes:
    buf = BytesIO()
    Image.new("RGB", (20, 20), "white").save(buf, format="PNG")
    return buf.getvalue()


def _pdf_bytes(pages: int = 2) -> bytes:
    imgs = [Image.new("RGB", (30, 30), "white") for _ in range(pages)]
    buf = BytesIO()
    imgs[0].save(buf, format="PDF", save_all=True, append_images=imgs[1:])
    return buf.getvalue()


def test_image_passthrough():
    images = extraction._to_images(_png_bytes(), "image/png")
    assert len(images) == 1
    assert images[0][1] == "image/png"


def test_pdf_rasterized_to_page_images():
    images = extraction._to_images(_pdf_bytes(2), "application/pdf")
    assert len(images) == 2
    assert all(mt == "image/png" for _, mt in images)


def test_unsupported_type_rejected():
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        extraction._to_images(b"x", "text/plain")
    assert exc.value.status_code == 400


def test_parse_json_handles_code_fences():
    out = extraction._parse_json('```json\n{"a": 1}\n```')
    assert out == {"a": 1}


def test_extract_openai_parses_structured_output(monkeypatch):
    captured = {}

    async def fake_create(**kwargs):
        captured.update(kwargs)
        payload = {"document_type": "marksheet", "name": "Asha", "roll_number": 42}
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(payload)))]
        )

    fake_client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=fake_create))
    )
    monkeypatch.setattr(extraction, "_get_openai_client", lambda: fake_client)
    # llm_provider defaults to "openai", so extract() takes the OpenAI path.

    result = asyncio.run(extraction.extract(_png_bytes(), "image/png", _doc_type()))
    assert result["name"] == "Asha"
    assert result["roll_number"] == 42

    # The request carried a json_schema response_format and an image content block.
    assert captured["response_format"]["type"] == "json_schema"
    user_content = captured["messages"][1]["content"]
    assert any(c["type"] == "image_url" for c in user_content)
