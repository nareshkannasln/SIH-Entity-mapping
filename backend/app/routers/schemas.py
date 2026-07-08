"""Doc-type (schema) management endpoints.

Doc types are user-editable data, which is what makes the product general-purpose.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status

from .. import db
from ..models import DocType, DocTypeIn
from ..security import get_current_user

router = APIRouter(prefix="/api/doc-types", tags=["doc-types"])


def _to_doc_type(doc: dict) -> DocType:
    doc.pop("_id", None)
    return DocType(**doc)


@router.get("", response_model=list[DocType])
async def list_doc_types(_: str = Depends(get_current_user)):
    return [_to_doc_type(d) async for d in db.doc_types().find().sort("label", 1)]


@router.get("/{key}", response_model=DocType)
async def get_doc_type(key: str, _: str = Depends(get_current_user)):
    doc = await db.doc_types().find_one({"key": key})
    if not doc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Doc type not found")
    return _to_doc_type(doc)


@router.post("", response_model=DocType, status_code=status.HTTP_201_CREATED)
async def create_doc_type(payload: DocTypeIn, username: str = Depends(get_current_user)):
    if await db.doc_types().find_one({"key": payload.key}):
        raise HTTPException(status.HTTP_409_CONFLICT, "Doc type key already exists")
    doc = {
        **payload.model_dump(),
        "created_by": username,
        "created_at": datetime.now(timezone.utc),
    }
    await db.doc_types().insert_one(doc)
    return _to_doc_type(doc)


@router.put("/{key}", response_model=DocType)
async def update_doc_type(key: str, payload: DocTypeIn, username: str = Depends(get_current_user)):
    if payload.key != key:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Key in body must match URL")
    existing = await db.doc_types().find_one({"key": key})
    if not existing:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Doc type not found")
    update = {"label": payload.label, "fields": [f.model_dump() for f in payload.fields]}
    await db.doc_types().update_one({"key": key}, {"$set": update})
    return await get_doc_type(key, username)
