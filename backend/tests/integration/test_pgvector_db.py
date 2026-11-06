"""Integration tests against a real PostgreSQL + pgvector database.

Run with DATABASE_URL pointing at a disposable database that has been migrated
(`alembic upgrade head`). Skipped automatically when no database is reachable.
"""
import uuid

import pytest
from sqlalchemy import text

from app.database import SessionLocal, engine


def _db_available() -> bool:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1 FROM embeddings LIMIT 0"))
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _db_available(), reason="needs a migrated PostgreSQL + pgvector database")


@pytest.fixture
def seeded():
    from app.models import Chat, Document, Embedding, User

    db = SessionLocal()
    suffix = uuid.uuid4().hex[:8]
    user = User(name="t", email=f"t-{suffix}@example.com", password_hash="x", monthly_budget_micro_usd=1, spent_micro_usd=0)
    db.add(user)
    db.flush()
    chats = [Chat(user_id=user.id, local_id=i, name=f"c{i}") for i in (1, 2)]
    db.add_all(chats)
    db.flush()
    doc = Document(user_id=user.id, chat_id=chats[0].id, filename="a.pdf", content="")
    db.add(doc)
    db.flush()

    def vec(i: int) -> list[float]:
        v = [0.0] * 384
        v[i] = 1.0
        return v

    db.add_all([
        Embedding(id=uuid.uuid4(), user_id=user.id, document_id=doc.id, chat_id=chats[0].id,
                  content=f"chunk-{i}", embedding=vec(i), chunk_metadata={"page": i, "filename": "a.pdf"})
        for i in range(3)
    ] + [
        Embedding(id=uuid.uuid4(), user_id=user.id, document_id=None, chat_id=chats[1].id,
                  content="other-chat", embedding=vec(0), chunk_metadata={"page": 9, "filename": "b.pdf"})
    ])
    db.commit()
    yield user, chats
    from app.repositories import chat_repository
    for chat in chats:
        chat_repository.delete_chat(db, chat.local_id, user.id)
    db.delete(db.get(User, user.id))
    db.commit()
    db.close()


def test_query_similar_orders_by_cosine_distance_and_filters_by_chat(seeded):
    from app.repositories.pgvector_repository import query_similar

    user, chats = seeded
    query = [0.0] * 384
    query[1] = 1.0
    result = query_similar(query, n_results=2, user_id=user.id, chat_id=chats[0].id)

    assert result["documents"][0] == ["chunk-1", result["documents"][0][1]]
    assert result["distances"][0][0] == pytest.approx(0.0)
    assert result["distances"][0][1] == pytest.approx(1.0)
    assert "other-chat" not in result["documents"][0]
    assert result["metadatas"][0][0]["page"] == 1


def test_delete_chat_with_embeddings_and_documents(seeded):
    from app.models import Embedding
    from app.repositories import chat_repository

    user, chats = seeded
    db = SessionLocal()
    try:
        assert chat_repository.delete_chat(db, chats[0].local_id, user.id) is True
        assert db.query(Embedding).filter(Embedding.chat_id == chats[0].id).count() == 0
    finally:
        db.close()
