"""Unit tests for the extraction schema builder and verification engine.

The Claude client is never called here — extraction is tested at the schema level
and verification is pure logic.
"""

from app.extraction import build_json_schema
from app.models import DocType, SchemaField
from app.verification import verify


def _marksheet() -> DocType:
    return DocType(
        key="marksheet",
        label="Marksheet",
        fields=[
            SchemaField(name="name", type="string"),
            SchemaField(name="roll_number", type="integer"),
        ],
    )


def test_build_json_schema_includes_document_type_and_fields():
    schema = build_json_schema(_marksheet())
    assert schema["additionalProperties"] is False
    assert "document_type" in schema["properties"]
    assert schema["properties"]["roll_number"]["type"] == ["integer", "null"]
    assert set(schema["required"]) == {"document_type", "name", "roll_number"}


def test_verify_all_match():
    extracted = {"document_type": "marksheet", "name": "Asha", "roll_number": 42}
    reference = {"name": "asha", "roll_number": "42"}
    result = verify(_marksheet(), extracted, "m.pdf", reference)
    assert result.overall_status == "matched"
    assert result.doc_type_mismatch is False
    assert all(fr.status == "match" for fr in result.field_results)


def test_verify_mismatch_and_missing():
    extracted = {"document_type": "marksheet", "name": "Asha", "roll_number": None}
    reference = {"name": "Bhavna", "roll_number": "42"}
    result = verify(_marksheet(), extracted, "m.pdf", reference)
    assert result.overall_status == "mismatched"
    statuses = {fr.field: fr.status for fr in result.field_results}
    assert statuses["name"] == "mismatch"
    assert statuses["roll_number"] == "missing"


def test_verify_without_reference_is_extracted_only():
    extracted = {"document_type": "marksheet", "name": "Asha", "roll_number": 42}
    result = verify(_marksheet(), extracted, "m.pdf", None)
    assert result.overall_status == "extracted"
    assert {fr.status for fr in result.field_results} == {"no_reference"}


def test_doc_type_mismatch_detected():
    extracted = {"document_type": "aadhaar", "name": "Asha", "roll_number": 42}
    result = verify(_marksheet(), extracted, "m.pdf", None)
    assert result.doc_type_mismatch is True
