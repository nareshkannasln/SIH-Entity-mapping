"""Compare extracted fields against caller-supplied reference values.

This formalizes the original (unused) ``compare_values`` idea into the actual
product output: a per-field match/mismatch report the old UI never surfaced.
"""

from typing import Any

from .models import DocType, FieldResult, VerificationResult


def _normalize(value: Any) -> str:
    return str(value).strip().lower() if value is not None else ""


def verify(
    doc_type: DocType,
    extracted: dict[str, Any],
    filename: str,
    reference: dict[str, Any] | None = None,
) -> VerificationResult:
    reference = reference or {}
    detected = extracted.get("document_type")
    # Mismatch only if the model confidently detected a *different* type.
    mismatch = bool(detected) and _normalize(detected) != _normalize(doc_type.key) \
        and _normalize(detected) != _normalize(doc_type.label)

    field_results: list[FieldResult] = []
    any_reference = False
    any_field_mismatch = False

    for field in doc_type.fields:
        value = extracted.get(field.name)
        if field.name in reference and reference[field.name] not in (None, ""):
            any_reference = True
            expected = reference[field.name]
            if value in (None, ""):
                fstatus = "missing"
                any_field_mismatch = True
            elif _normalize(value) == _normalize(expected):
                fstatus = "match"
            else:
                fstatus = "mismatch"
                any_field_mismatch = True
            field_results.append(
                FieldResult(field=field.name, extracted=value, expected=expected, status=fstatus)
            )
        else:
            fstatus = "missing" if value in (None, "") and field.required else "no_reference"
            field_results.append(
                FieldResult(field=field.name, extracted=value, expected=None, status=fstatus)
            )

    if any_reference:
        overall = "mismatched" if any_field_mismatch else "matched"
    else:
        overall = "extracted"

    return VerificationResult(
        doc_type=doc_type.key,
        filename=filename,
        document_type_detected=detected,
        doc_type_mismatch=mismatch,
        extracted={k: v for k, v in extracted.items() if k != "document_type"},
        field_results=field_results,
        overall_status=overall,
    )
