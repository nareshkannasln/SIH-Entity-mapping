"""Document verification endpoints: run extraction + verification, view history."""

import json
from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from .. import db
from ..extraction import extract
from ..models import DocType, VerificationResult
from ..security import get_current_user
from ..verification import verify

router = APIRouter(prefix="/api", tags=["documents"])


@router.post("/verify", response_model=VerificationResult)
async def verify_document(
    doc_type: str = Form(...),
    file: UploadFile = File(...),
    reference: str | None = Form(None),
    username: str = Depends(get_current_user),
):
    dt_doc = await db.doc_types().find_one({"key": doc_type})
    if not dt_doc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Unknown doc type '{doc_type}'")
    dt_doc.pop("_id", None)
    doc_type_model = DocType(**dt_doc)

    reference_data = None
    if reference:
        try:
            reference_data = json.loads(reference)
            if not isinstance(reference_data, dict):
                raise ValueError
        except (json.JSONDecodeError, ValueError):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "reference must be a JSON object")

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Empty file")

    extraction = await extract(file_bytes, file.content_type or "", doc_type_model)
    result = verify(doc_type_model, extraction.data, file.filename or "document", reference_data)
    result.engine = extraction.engine

    record = result.model_dump()
    record.update({"created_by": username, "created_at": datetime.now(timezone.utc)})
    insert = await db.verifications().insert_one(record)
    result.id = str(insert.inserted_id)
    result.created_at = record["created_at"]
    return result


@router.get("/verifications", response_model=list[VerificationResult])
async def list_verifications(username: str = Depends(get_current_user)):
    out: list[VerificationResult] = []
    cursor = db.verifications().find({"created_by": username}).sort("created_at", -1).limit(100)
    async for doc in cursor:
        doc["id"] = str(doc.pop("_id"))
        doc.pop("created_by", None)
        out.append(VerificationResult(**doc))
    return out


@router.get("/verifications/{verification_id}", response_model=VerificationResult)
async def get_verification(verification_id: str, username: str = Depends(get_current_user)):
    try:
        oid = ObjectId(verification_id)
    except InvalidId:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid id")
    doc = await db.verifications().find_one({"_id": oid, "created_by": username})
    if not doc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Verification not found")
    doc["id"] = str(doc.pop("_id"))
    doc.pop("created_by", None)
    return VerificationResult(**doc)
