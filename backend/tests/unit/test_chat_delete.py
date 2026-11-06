"""delete_chat must remove every row that references the chat before deleting it.

A table with a foreign key to chats.id that delete_chat forgets makes chat
deletion fail with an IntegrityError (this happened with the old quiz tables).
"""
from unittest.mock import MagicMock

import app.models  # noqa: F401 - registers every model on Base.metadata
from app.database import Base
from app.models.chat import Chat
from app.repositories import chat_repository


def _tables_referencing(table_name: str) -> set[str]:
    referencing = set()
    for table in Base.metadata.tables.values():
        for fk in table.foreign_keys:
            if fk.column.table.name == table_name:
                referencing.add(table.name)
    return referencing


class _RecordingSession:
    def __init__(self, chat):
        self.chat = chat
        self.deleted_tables: list[str] = []
        self.deleted_objects = []
        self.committed = False

    def query(self, model):
        query = MagicMock()
        if model is Chat:
            query.filter.return_value.first.return_value = self.chat
        else:
            query.filter.return_value.delete.side_effect = (
                lambda *a, **k: self.deleted_tables.append(model.__tablename__)
            )
        return query

    def delete(self, obj):
        self.deleted_objects.append(obj)

    def commit(self):
        self.committed = True


def test_delete_chat_clears_every_table_referencing_chats():
    chat = Chat(id=7, user_id=1, local_id=1, name="c")
    db = _RecordingSession(chat)

    assert chat_repository.delete_chat(db, chat_id=1, user_id=1) is True

    expected = _tables_referencing("chats")
    assert expected, "sanity: some tables reference chats"
    assert expected <= set(db.deleted_tables)
    assert db.deleted_objects == [chat]
    assert db.committed


def test_embeddings_deleted_before_documents():
    db = _RecordingSession(Chat(id=7, user_id=1, local_id=1, name="c"))
    chat_repository.delete_chat(db, chat_id=1, user_id=1)
    assert db.deleted_tables.index("embeddings") < db.deleted_tables.index("documents")


def test_delete_chat_missing_returns_false():
    db = _RecordingSession(None)
    assert chat_repository.delete_chat(db, chat_id=1, user_id=1) is False
    assert db.deleted_tables == []
