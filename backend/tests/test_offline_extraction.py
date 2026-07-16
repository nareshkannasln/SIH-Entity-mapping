"""Tests for the offline OCR+NER engine's pure text->fields mapping.

These exercise ``extract_fields_from_text`` directly with sample OCR text, so no
Tesseract binary and no spaCy model are required to run them.
"""

from app.models import DocType, SchemaField
from app.offline_extraction import (
    _classify_document,
    _find_labeled_value,
    _labels_for,
    extract_fields_from_text,
)


def _marksheet() -> DocType:
    return DocType(
        key="marksheet",
        label="Marksheet",
        fields=[
            SchemaField(name="name"),
            SchemaField(name="date_of_birth", type="date"),
            SchemaField(name="father_name"),
            SchemaField(name="roll_number"),
        ],
    )


MARKSHEET_OCR = """
BOARD OF SECONDARY EDUCATION
STATEMENT OF MARKS

Name: Asha Kumari
Father's Name: Ramesh Kumar
Date of Birth: 14-03-2001
Roll Number: 785412

Subject            Marks Obtained
Mathematics        95
Science            88
"""


def test_labels_prioritise_specific_over_generic():
    labels = _labels_for(SchemaField(name="father_name"))
    # "father's name" (specific) should sort before the bare "father".
    assert labels[0] == "father's name"


def test_find_labeled_value_reads_colon_delimited():
    lines = [ln.strip() for ln in MARKSHEET_OCR.splitlines() if ln.strip()]
    assert _find_labeled_value(lines, ["name"]) == "Asha Kumari"


def test_marksheet_fields_extracted():
    result = extract_fields_from_text(MARKSHEET_OCR, _marksheet())
    assert result["name"] == "Asha Kumari"
    assert result["father_name"] == "Ramesh Kumar"
    assert result["date_of_birth"] == "14-03-2001"
    assert result["roll_number"] == "785412"


def test_generic_name_not_matched_inside_surname():
    # "name" must not be captured from the word "Surname".
    lines = ["Surname: Verma", "Name: Priya"]
    assert _find_labeled_value(lines, ["name"]) == "Priya"


def test_document_type_classified():
    assert _classify_document(MARKSHEET_OCR, "aadhaar") == "marksheet"


def test_aadhaar_number_and_type_coercion():
    ocr = """
    Government of India
    UNIQUE IDENTIFICATION AUTHORITY OF INDIA
    Name: Rohan Das
    DOB: 05/09/1990
    Aadhaar: 1234 5678 9012
    """
    dt = DocType(
        key="aadhaar",
        label="Aadhaar Card",
        fields=[
            SchemaField(name="name"),
            SchemaField(name="aadhaar_number"),
            SchemaField(name="date_of_birth", type="date"),
        ],
    )
    result = extract_fields_from_text(ocr, dt)
    assert result["document_type"] == "aadhaar"
    assert result["aadhaar_number"] == "123456789012"
    assert result["date_of_birth"] == "05/09/1990"


def test_numeric_fields_coerced():
    ocr = "Candidate Name: Meera\nGATE Score: 742\nCGPA: 8.65\nYear: 2023"
    dt = DocType(
        key="gate_score_card",
        label="GATE Score Card",
        fields=[
            SchemaField(name="name"),
            SchemaField(name="gate_score", type="integer"),
            SchemaField(name="cgpa", type="number"),
            SchemaField(name="year", type="integer"),
        ],
    )
    result = extract_fields_from_text(ocr, dt)
    assert result["gate_score"] == 742
    assert result["cgpa"] == 8.65
    assert result["year"] == 2023


def test_missing_field_is_none():
    result = extract_fields_from_text("Name: Solo", _marksheet())
    assert result["name"] == "Solo"
    assert result["roll_number"] is None


def test_empty_text_yields_nulls():
    result = extract_fields_from_text("", _marksheet())
    assert result["name"] is None
    assert set(result) == {"document_type", "name", "date_of_birth", "father_name", "roll_number"}


def test_offline_extract_returns_fields_and_text():
    """``extract()`` does ``data, text = offline_extract(...)`` — keep that contract.

    Regression: this returned a bare dict, so every offline request unpacked the
    dict's keys and blew up with a ValueError before reaching the caller.
    """
    from unittest.mock import patch

    from app.offline_extraction import offline_extract

    with patch("app.offline_extraction.to_images", return_value=[(b"x", "image/png")]), patch(
        "app.offline_extraction._ocr_images", return_value="Name: Solo\nRoll Number: 42"
    ), patch("app.offline_extraction.get_settings") as gs:
        gs.return_value.ocr_engine = "tesseract"
        data, text = offline_extract(b"x", "image/png", _marksheet())

    assert data["name"] == "Solo"
    assert text == "Name: Solo\nRoll Number: 42"


def test_html_to_text_keeps_surya_lines_separate():
    """Surya returns HTML blocks; tags must become newlines, not disappear.

    If they collapse, ``Name: X`` runs into the next label and the rules break.
    """
    from app.offline_extraction import _html_to_text

    assert _html_to_text("<p>Name: Test Person</p>") == "Name: Test Person"
    assert _html_to_text("<p>Name: A</p><p>Gender: Male</p>") == "Name: A\nGender: Male"
    assert _html_to_text("<p>Line one<br>Line two</p>") == "Line one\nLine two"
