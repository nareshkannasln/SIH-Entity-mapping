"""Password-hashing and JWT round-trip tests (no DB required)."""

import jwt
import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.config import get_settings
from app.security import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)


def _creds(token: str) -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


def test_password_hash_is_not_plaintext_and_verifies():
    h = hash_password("s3cret-password")
    assert h != "s3cret-password"
    assert verify_password("s3cret-password", h)
    assert not verify_password("wrong", h)


def test_token_round_trip():
    token = create_access_token("alice")
    assert get_current_user(_creds(token)) == "alice"


def test_invalid_token_rejected():
    with pytest.raises(HTTPException) as exc:
        get_current_user(_creds("not-a-token"))
    assert exc.value.status_code == 401


def test_wrong_secret_rejected():
    settings = get_settings()
    forged = jwt.encode({"sub": "mallory"}, "different-secret", algorithm=settings.jwt_algorithm)
    with pytest.raises(HTTPException) as exc:
        get_current_user(_creds(forged))
    assert exc.value.status_code == 401
