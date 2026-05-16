"""MongoDB-backed chat conversations and messages."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

try:
    from pymongo import ASCENDING, DESCENDING, MongoClient
except ImportError:
    MongoClient = None
    ASCENDING = DESCENDING = 1

logger = logging.getLogger(__name__)

CONVERSATIONS_COL = "chat_conversations"
MESSAGES_COL = "chat_messages"
MAX_TITLE_LEN = 56
MAX_HISTORY_MESSAGES = 14


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _get_db(mongo_uri: str, mongo_db: str):
    if MongoClient is None:
        raise RuntimeError("pymongo is not installed. Run: pip install pymongo")
    client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
    client.admin.command("ping")
    return client, client[mongo_db]


def _ensure_indexes(db) -> None:
    conv = db[CONVERSATIONS_COL]
    msgs = db[MESSAGES_COL]
    conv.create_index([("updated_at", DESCENDING)])
    msgs.create_index([("conversation_id", ASCENDING), ("seq", ASCENDING)])


def make_title(text: str) -> str:
    clean = " ".join(text.strip().split())
    if len(clean) <= MAX_TITLE_LEN:
        return clean or "New chat"
    return clean[: MAX_TITLE_LEN - 1].rstrip() + "…"


def list_conversations(mongo_uri: str, mongo_db: str, limit: int = 60) -> list[dict]:
    client = None
    try:
        client, db = _get_db(mongo_uri, mongo_db)
        _ensure_indexes(db)
        cursor = db[CONVERSATIONS_COL].find(
            {},
            {"_id": 0, "id": 1, "title": 1, "created_at": 1, "updated_at": 1},
        ).sort("updated_at", DESCENDING).limit(limit)
        out = []
        for doc in cursor:
            for key in ("created_at", "updated_at"):
                if isinstance(doc.get(key), datetime):
                    doc[key] = doc[key].isoformat()
            out.append(doc)
        return out
    finally:
        if client is not None:
            client.close()


def create_conversation(
    mongo_uri: str,
    mongo_db: str,
    title: str = "New chat",
) -> dict:
    client = None
    now = _utcnow()
    conv_id = str(uuid4())
    doc = {
        "id": conv_id,
        "title": title or "New chat",
        "created_at": now,
        "updated_at": now,
    }
    try:
        client, db = _get_db(mongo_uri, mongo_db)
        _ensure_indexes(db)
        db[CONVERSATIONS_COL].insert_one(doc.copy())
        return {
            "id": conv_id,
            "title": doc["title"],
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }
    finally:
        if client is not None:
            client.close()


def delete_conversation(mongo_uri: str, mongo_db: str, conversation_id: str) -> bool:
    client = None
    try:
        client, db = _get_db(mongo_uri, mongo_db)
        r = db[CONVERSATIONS_COL].delete_one({"id": conversation_id})
        db[MESSAGES_COL].delete_many({"conversation_id": conversation_id})
        return r.deleted_count > 0
    finally:
        if client is not None:
            client.close()


def get_messages(
    mongo_uri: str,
    mongo_db: str,
    conversation_id: str,
    limit: int = 200,
) -> list[dict]:
    client = None
    try:
        client, db = _get_db(mongo_uri, mongo_db)
        cursor = db[MESSAGES_COL].find(
            {"conversation_id": conversation_id},
            {"_id": 0, "role": 1, "content": 1, "sources": 1, "created_at": 1, "seq": 1},
        ).sort("seq", ASCENDING).limit(limit)
        out = []
        for doc in cursor:
            if isinstance(doc.get("created_at"), datetime):
                doc["created_at"] = doc["created_at"].isoformat()
            out.append(doc)
        return out
    finally:
        if client is not None:
            client.close()


def get_history_for_prompt(
    mongo_uri: str,
    mongo_db: str,
    conversation_id: str,
    limit: int = MAX_HISTORY_MESSAGES,
) -> list[dict]:
    """Recent messages excluding the one about to be added."""
    msgs = get_messages(mongo_uri, mongo_db, conversation_id, limit=limit + 5)
    if len(msgs) > limit:
        msgs = msgs[-limit:]
    return [{"role": m["role"], "content": m["content"]} for m in msgs]


def append_message(
    mongo_uri: str,
    mongo_db: str,
    conversation_id: str,
    role: str,
    content: str,
    sources: Optional[list] = None,
    set_title_from_first_user: bool = False,
) -> dict:
    client = None
    now = _utcnow()
    try:
        client, db = _get_db(mongo_uri, mongo_db)
        _ensure_indexes(db)

        last = db[MESSAGES_COL].find_one(
            {"conversation_id": conversation_id},
            sort=[("seq", DESCENDING)],
            projection={"seq": 1},
        )
        seq = (last.get("seq", 0) + 1) if last else 1

        msg = {
            "conversation_id": conversation_id,
            "role": role,
            "content": content,
            "seq": seq,
            "created_at": now,
        }
        if sources is not None:
            msg["sources"] = sources
        db[MESSAGES_COL].insert_one(msg)

        update: dict[str, Any] = {"updated_at": now}
        if set_title_from_first_user and role == "user":
            update["title"] = make_title(content)
        db[CONVERSATIONS_COL].update_one(
            {"id": conversation_id},
            {"$set": update},
        )

        return {
            "role": role,
            "content": content,
            "seq": seq,
            "created_at": now.isoformat(),
        }
    finally:
        if client is not None:
            client.close()


def save_exchange(
    mongo_uri: str,
    mongo_db: str,
    conversation_id: str,
    user_text: str,
    assistant_text: str,
    sources: Optional[list] = None,
) -> None:
    if not conversation_id or not user_text.strip():
        return
    existing = get_messages(mongo_uri, mongo_db, conversation_id, limit=1)
    is_first = len(existing) == 0
    append_message(
        mongo_uri, mongo_db, conversation_id, "user", user_text.strip(),
        set_title_from_first_user=is_first,
    )
    append_message(
        mongo_uri, mongo_db, conversation_id, "assistant",
        assistant_text.strip(), sources=sources,
    )
