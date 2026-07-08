"""Pydantic models for API requests/responses and stored documents.

Doc types (and their fields) are *data*, not code — this is what makes the
product general-purpose rather than hardcoded to recruitment.
"""

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, EmailStr, Field

FieldType = Literal["string", "integer", "number", "boolean", "date"]


# --- Auth ---
class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserPublic(BaseModel):
    username: str
    email: EmailStr


# --- Doc types (schemas) ---
class SchemaField(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    type: FieldType = "string"
    description: str = ""
    required: bool = True


class DocTypeIn(BaseModel):
    key: str = Field(min_length=1, max_length=64, pattern=r"^[a-z0-9_]+$")
    label: str = Field(min_length=1, max_length=128)
    fields: list[SchemaField] = Field(min_length=1)


class DocType(DocTypeIn):
    created_by: Optional[str] = None
    created_at: Optional[datetime] = None


# --- Verification ---
class FieldResult(BaseModel):
    field: str
    extracted: Any = None
    expected: Any = None
    # "match" | "mismatch" | "missing" | "no_reference"
    status: str


class VerificationResult(BaseModel):
    id: Optional[str] = None
    doc_type: str
    filename: str
    document_type_detected: Optional[str] = None
    doc_type_mismatch: bool = False
    extracted: dict[str, Any] = {}
    field_results: list[FieldResult] = []
    overall_status: str = "extracted"  # "matched" | "mismatched" | "extracted"
    created_at: Optional[datetime] = None
