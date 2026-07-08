"""Async MongoDB access via Motor.

Connection details come entirely from settings/env — no hardcoded credentials.
"""

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from .config import get_settings

_client: AsyncIOMotorClient | None = None


def get_client() -> AsyncIOMotorClient:
    global _client
    if _client is None:
        settings = get_settings()
        _client = AsyncIOMotorClient(settings.mongo_uri)
    return _client


def get_db() -> AsyncIOMotorDatabase:
    return get_client()[get_settings().mongo_db]


# Collection accessors
def users():
    return get_db()["users"]


def doc_types():
    return get_db()["doc_types"]


def verifications():
    return get_db()["verifications"]


async def ensure_indexes() -> None:
    await users().create_index("username", unique=True)
    await doc_types().create_index("key", unique=True)
    await verifications().create_index([("created_by", 1), ("created_at", -1)])


def close_client() -> None:
    global _client
    if _client is not None:
        _client.close()
        _client = None
