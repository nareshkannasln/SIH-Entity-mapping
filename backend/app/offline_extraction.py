"""Offline document extraction — a custom OCR + NER engine (no API, no GPU).

This is the ``offline`` provider. It runs entirely on the local CPU and needs no
API key, which makes it the reliable zero-config default and a fallback when no
cloud model is configured. The pipeline is three classical-ML / NLP stages:

    page images ──► Tesseract OCR ──► raw text
                                        │
                    ┌───────────────────┴───────────────────┐
                    ▼                                        ▼
          rule engine (regex + label/                spaCy NER model
          fuzzy matching, per field)                 (PERSON / ORG / GPE)
                    └───────────────────┬───────────────────┘
                                        ▼
                        {field: value}  +  document_type

The heavy lifting — ``extract_fields_from_text`` — is a pure function of the OCR
text and the target schema, so it is unit-tested without Tesseract or a GPU. The
spaCy model is optional: if it isn't installed the engine degrades gracefully to
its regex + label-matching rules.
"""

from __future__ import annotations

import logging
import re
from difflib import SequenceMatcher
from functools import lru_cache
from typing import Any

from fastapi import HTTPException, status

from .config import get_settings
from .images import to_images
from .models import DocType, SchemaField

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
# Synonyms: map a schema field name to the labels a document is likely to use.
# --------------------------------------------------------------------------- #
_FIELD_SYNONYMS: dict[str, list[str]] = {
    "name": ["name", "candidate name", "student name", "full name", "holder name", "employee name"],
    "father_name": ["father's name", "fathers name", "father name", "father", "s/o", "son of"],
    "mother_name": ["mother's name", "mothers name", "mother name", "mother", "d/o", "daughter of"],
    "date_of_birth": ["date of birth", "dob", "d.o.b", "birth date", "born on"],
    "aadhaar_number": ["aadhaar number", "aadhaar", "aadhar", "uid", "vid"],
    "address": ["address", "residence", "residential address"],
    "gender": ["gender", "sex"],
    "roll_number": ["roll number", "roll no", "roll", "registration number", "reg no"],
    "registration_number": ["registration number", "registration no", "reg no", "enrolment number"],
    "university": ["university", "institute", "college", "board of", "board"],
    "organization": ["organization", "organisation", "company", "employer", "firm"],
    "degree": ["degree", "programme", "program", "course"],
    "qualification_degree": ["qualification", "specialization", "specialisation", "branch", "discipline"],
    "cgpa": ["cgpa", "gpa", "grade point average"],
    "percentage": ["percentage", "percent", "marks percentage"],
    "year": ["year of passing", "passing year", "year", "session"],
    "passing_year": ["year of passing", "passing year", "year"],
    "gate_score": ["gate score", "score"],
    "all_india_rank": ["all india rank", "air", "rank"],
    "marks_out_of_100": ["marks out of 100", "marks", "total marks"],
    "from_date": ["date of joining", "from", "start date", "joining date"],
    "to_date": ["date of leaving", "to", "end date", "relieving date"],
    "email": ["email", "e-mail", "email id"],
}

# Named-entity kind expected for name-like / org-like / place-like fields.
_PERSON_HINTS = ("name", "candidate", "student", "holder", "graduate", "employee")
_ORG_HINTS = ("university", "organization", "organisation", "company", "employer", "institute", "board", "college")
_PLACE_HINTS = ("address", "residence", "city", "state", "place")

# Keyword signatures used to classify what a document actually is.
_DOC_KEYWORDS: dict[str, list[str]] = {
    "aadhaar": ["aadhaar", "aadhar", "unique identification", "uidai", "government of india"],
    "birth_cert": ["birth certificate", "registration of birth", "municipal", "date of birth"],
    "marksheet": ["marksheet", "mark sheet", "statement of marks", "grade card", "marks obtained"],
    "degree_cert": ["degree", "bachelor of", "master of", "has been conferred", "awarded the degree"],
    "provisional_cert": ["provisional certificate", "provisionally"],
    "gate_score_card": ["gate", "graduate aptitude test", "gate score"],
    "experience_cert": ["experience certificate", "to whom it may concern", "relieved", "employed with"],
    "pan": ["permanent account number", "income tax department"],
}

_DATE_RE = re.compile(
    r"\b("
    r"\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4}"  # 12-05-1998, 12/05/98
    r"|\d{4}[-/.]\d{1,2}[-/.]\d{1,2}"   # 1998-05-12
    r"|\d{1,2}\s+[A-Za-z]{3,9},?\s+\d{4}"  # 12 May 1998
    r"|[A-Za-z]{3,9}\s+\d{1,2},?\s+\d{4}"  # May 12, 1998
    r")\b"
)
_AADHAAR_RE = re.compile(r"\b(\d{4}\s?\d{4}\s?\d{4})\b")
_EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
_YEAR_RE = re.compile(r"\b(19|20)\d{2}\b")
_NUMBER_RE = re.compile(r"-?\d+(?:\.\d+)?")
_INT_RE = re.compile(r"-?\d+")
# A run of 3+ spaces usually separates OCR columns — a value ends there.
_COLUMN_GAP_RE = re.compile(r"\s{3,}")


# --------------------------------------------------------------------------- #
# spaCy NER (optional, lazily loaded).
# --------------------------------------------------------------------------- #
@lru_cache(maxsize=1)
def _load_nlp():
    """Load the spaCy model once, or return None if spaCy/the model is missing."""
    model = get_settings().spacy_model
    try:
        import spacy

        return spacy.load(model)
    except Exception:  # pragma: no cover - depends on optional install
        logger.info("spaCy model '%s' unavailable; using rule-based extraction only.", model)
        return None


def _ner_entities(text: str) -> dict[str, list[str]]:
    """Return {entity_label: [values]} from spaCy, or {} when unavailable."""
    nlp = _load_nlp()
    if nlp is None:
        return {}
    out: dict[str, list[str]] = {}
    for ent in nlp(text[:100_000]).ents:
        out.setdefault(ent.label_, []).append(ent.text.strip())
    return out


# --------------------------------------------------------------------------- #
# Text helpers.
# --------------------------------------------------------------------------- #
def _labels_for(field: SchemaField) -> list[str]:
    """All labels to search for a field, most-specific first."""
    labels = list(_FIELD_SYNONYMS.get(field.name, []))
    spaced = field.name.replace("_", " ").strip().lower()
    if spaced and spaced not in labels:
        labels.append(spaced)
    # Longer labels first so "father's name" wins over the bare "name".
    return sorted(dict.fromkeys(labels), key=len, reverse=True)


def _clean_value(value: str) -> str:
    """Trim a captured value to the first cell and strip label punctuation."""
    value = _COLUMN_GAP_RE.split(value, maxsplit=1)[0]
    value = value.strip(" \t:.-–—|)(•")
    return value.strip()


def _find_labeled_value(lines: list[str], labels: list[str]) -> str | None:
    """Find ``Label: value`` (or value on the next line) for any of ``labels``."""
    for i, line in enumerate(lines):
        low = line.lower()
        for label in labels:
            idx = low.find(label)
            if idx == -1:
                continue
            # Require a non-alphanumeric char just before the label so "name"
            # doesn't match inside "surname".
            if idx > 0 and (low[idx - 1].isalnum()):
                continue
            rest = line[idx + len(label):]
            # The value follows an optional delimiter.
            rest = rest.lstrip(" \t")
            rest = re.sub(r"^[:\-–—=|.]+\s*", "", rest)
            value = _clean_value(rest)
            if not value and i + 1 < len(lines):
                value = _clean_value(lines[i + 1])
            if value:
                return value
    return None


def _fuzzy_labeled_value(lines: list[str], labels: list[str], threshold: float = 0.82) -> str | None:
    """Fallback for OCR typos: fuzzy-match the token(s) before a ':' delimiter."""
    for i, line in enumerate(lines):
        if ":" not in line:
            continue
        key, _, val = line.partition(":")
        key = key.strip().lower()
        if not key or len(key) > 40:
            continue
        for label in labels:
            if SequenceMatcher(None, key, label).ratio() >= threshold:
                value = _clean_value(val)
                if not value and i + 1 < len(lines):
                    value = _clean_value(lines[i + 1])
                if value:
                    return value
    return None


def _near_label_pattern(
    lines: list[str], labels: list[str], pattern: re.Pattern[str]
) -> str | None:
    """Find the first ``pattern`` match on a line that mentions any label."""
    for i, line in enumerate(lines):
        low = line.lower()
        if any(label in low for label in labels):
            for candidate in (line, lines[i + 1] if i + 1 < len(lines) else ""):
                m = pattern.search(candidate)
                if m:
                    return m.group(0)
    return None


def _coerce(value: Any, field_type: str) -> Any:
    """Coerce a captured string to the schema field's declared type."""
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if field_type == "integer":
        m = _INT_RE.search(text.replace(",", ""))
        return int(m.group(0)) if m else None
    if field_type == "number":
        m = _NUMBER_RE.search(text.replace(",", ""))
        return float(m.group(0)) if m else None
    if field_type == "boolean":
        low = text.lower()
        if low in ("yes", "true", "y", "1"):
            return True
        if low in ("no", "false", "n", "0"):
            return False
        return None
    return text


# --------------------------------------------------------------------------- #
# Per-field extraction.
# --------------------------------------------------------------------------- #
def _classify_document(text: str, requested_key: str) -> str:
    low = text.lower()
    scores = {key: sum(low.count(kw) for kw in kws) for key, kws in _DOC_KEYWORDS.items()}
    best = max(scores, key=scores.get) if scores else requested_key
    return best if scores.get(best, 0) > 0 else requested_key


def _field_kind(field: SchemaField) -> str:
    name = field.name.lower()
    if field.type == "date" or any(h in name for h in ("date", "dob", "_from", "_to")):
        return "date"
    if "aadhaar" in name or "aadhar" in name:
        return "aadhaar"
    if "email" in name:
        return "email"
    if any(h in name for h in _PERSON_HINTS) and "number" not in name:
        return "person"
    if any(h in name for h in _ORG_HINTS):
        return "org"
    if any(h in name for h in _PLACE_HINTS):
        return "place"
    if field.type in ("integer", "number"):
        return "number"
    return "generic"


def _first(values: list[str] | None) -> str | None:
    return values[0] if values else None


def _extract_one(
    field: SchemaField, text: str, lines: list[str], entities: dict[str, list[str]]
) -> Any:
    labels = _labels_for(field)
    kind = _field_kind(field)

    # 1) A labelled value is the strongest signal for every field kind.
    labeled = _find_labeled_value(lines, labels) or _fuzzy_labeled_value(lines, labels)

    if kind == "date":
        if labeled and (m := _DATE_RE.search(labeled)):
            return _coerce(m.group(0), field.type)
        near = _near_label_pattern(lines, labels, _DATE_RE)
        if near:
            return _coerce(near, field.type)
        m = _DATE_RE.search(text)
        return _coerce(m.group(0), field.type) if m else None

    if kind == "aadhaar":
        if labeled and (m := _AADHAAR_RE.search(labeled)):
            return m.group(1).replace(" ", "")
        m = _AADHAAR_RE.search(text)
        return m.group(1).replace(" ", "") if m else None

    if kind == "email":
        m = _EMAIL_RE.search(labeled or text)
        return m.group(0) if m else None

    if kind == "number":
        pattern = _YEAR_RE if "year" in field.name.lower() else _NUMBER_RE
        if labeled and (m := pattern.search(labeled.replace(",", ""))):
            return _coerce(m.group(0), field.type)
        near = _near_label_pattern(lines, labels, pattern)
        return _coerce(near, field.type) if near else None

    if kind in ("person", "org", "place"):
        if labeled:
            return _coerce(labeled, field.type)
        ner_label = {"person": "PERSON", "org": "ORG", "place": "GPE"}[kind]
        candidate = _first(entities.get(ner_label)) or (
            _first(entities.get("LOC")) if kind == "place" else None
        )
        return _coerce(candidate, field.type)

    return _coerce(labeled, field.type)


def extract_fields_from_text(text: str, doc_type: DocType) -> dict[str, Any]:
    """Map OCR text to the doc type's fields (pure, unit-tested, no I/O).

    Always includes ``document_type`` so a document/type mismatch can be flagged,
    mirroring the vision-LLM path's output shape.
    """
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    entities = _ner_entities(text) if text.strip() else {}

    result: dict[str, Any] = {"document_type": _classify_document(text, doc_type.key)}
    for field in doc_type.fields:
        try:
            result[field.name] = _extract_one(field, text, lines, entities)
        except Exception:  # never let one field break the whole extraction
            logger.exception("Offline extraction failed for field '%s'", field.name)
            result[field.name] = None
    return result


# --------------------------------------------------------------------------- #
# OCR entry point.
# --------------------------------------------------------------------------- #
def _ocr_images(images: list[tuple[bytes, str]]) -> str:
    """Run Tesseract over each page image and concatenate the text."""
    try:
        import pytesseract
        from PIL import Image
    except ImportError as exc:  # pragma: no cover - depends on optional install
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "Offline OCR is unavailable (pytesseract/Pillow not installed).",
        ) from exc

    from io import BytesIO

    lang = get_settings().ocr_languages
    pages: list[str] = []
    for img_bytes, _ in images:
        try:
            image = Image.open(BytesIO(img_bytes))
            pages.append(pytesseract.image_to_string(image, lang=lang))
        except pytesseract.TesseractNotFoundError as exc:
            raise HTTPException(
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                "Tesseract OCR is not installed on the server. Install the "
                "'tesseract-ocr' package, or switch to a cloud provider in Settings.",
            ) from exc
        except Exception:
            logger.exception("OCR failed on a page")
    return "\n".join(pages)


def offline_extract(file_bytes: bytes, content_type: str, doc_type: DocType) -> dict[str, Any]:
    """OCR the document locally, then map the text to the schema fields."""
    images = to_images(file_bytes, content_type)
    text = _ocr_images(images)
    if not text.strip():
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "No readable text was found in the document.",
        )
    return extract_fields_from_text(text, doc_type)
