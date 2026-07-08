"""Full-API integration test: register -> login -> doc-types -> verify -> history.

Requires a reachable MongoDB (MONGO_URI, default localhost). The Claude extraction
call is mocked — everything else (auth, seeding, persistence, verification) is real.
Skipped automatically if no MongoDB is reachable.
"""

import os

import pytest
from fastapi.testclient import TestClient
from pymongo import MongoClient
from pymongo.errors import PyMongoError

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")


def _mongo_available() -> bool:
    try:
        MongoClient(MONGO_URI, serverSelectionTimeoutMS=800).admin.command("ping")
        return True
    except PyMongoError:
        return False


pytestmark = pytest.mark.skipif(not _mongo_available(), reason="no MongoDB reachable")


@pytest.fixture
def client(monkeypatch):
    # Use an isolated DB per test run.
    monkeypatch.setenv("MONGO_DB", "docverify_test")
    from app.config import get_settings

    get_settings.cache_clear()

    from app import db
    from app.routers import documents

    # Mock the Claude extraction so no API key / network is needed.
    async def fake_extract(file_bytes, content_type, doc_type):
        return {
            "document_type": "marksheet",
            "name": "Asha Rao",
            "date_of_birth": "01-01-2000",
            "father_name": "Rao",
            "mother_name": "Meera",
            "roll_number": "12345",
        }

    monkeypatch.setattr(documents, "extract", fake_extract)

    from app.main import app

    with TestClient(app) as c:
        yield c

    MongoClient(MONGO_URI).drop_database("docverify_test")
    db.close_client()
    get_settings.cache_clear()


def _auth_header(client) -> dict:
    r = client.post(
        "/api/auth/register",
        json={"username": "asha", "email": "asha@example.com", "password": "password123"},
    )
    assert r.status_code == 201, r.text
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_full_flow(client):
    headers = _auth_header(client)

    # Seeded doc types are present.
    r = client.get("/api/doc-types", headers=headers)
    assert r.status_code == 200
    keys = {d["key"] for d in r.json()}
    assert {"marksheet", "aadhaar", "gate_score_card"} <= keys

    # Verify with a matching reference -> matched.
    r = client.post(
        "/api/verify",
        headers=headers,
        data={
            "doc_type": "marksheet",
            "reference": '{"name": "Asha Rao", "roll_number": "12345"}',
        },
        files={"file": ("m.pdf", b"%PDF-fake", "application/pdf")},
    )
    assert r.status_code == 200, r.text
    result = r.json()
    assert result["overall_status"] == "matched"
    assert result["doc_type_mismatch"] is False
    assert result["extracted"]["name"] == "Asha Rao"

    # History reflects it.
    r = client.get("/api/verifications", headers=headers)
    assert r.status_code == 200
    assert len(r.json()) == 1


def test_auth_required(client):
    # No Authorization header -> unauthenticated.
    assert client.get("/api/doc-types").status_code == 401


def test_login_wrong_password(client):
    _auth_header(client)
    r = client.post("/api/auth/login", json={"username": "asha", "password": "wrong"})
    assert r.status_code == 401
