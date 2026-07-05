from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.database import get_db
from app.models.chat import Chat
from app.models.document import Document
from app.models.ingestion_task import IngestionTask
from app.models.user import User
from app.routers.documents import router as documents_router


def _make_app_with_db(db):
    app = FastAPI()
    app.include_router(documents_router)
    app.dependency_overrides[get_db] = lambda: db
    return app


def test_direct_ingest_creates_a_task_for_each_uploaded_file(monkeypatch):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    User.__table__.create(bind=engine)
    Chat.__table__.create(bind=engine)
    Document.__table__.create(bind=engine)
    IngestionTask.__table__.create(bind=engine)

    db = SessionLocal()
    try:
        user = User(name='User', email='user@example.com', password_hash='hash')
        db.add(user)
        db.commit()
        db.refresh(user)

        chat = Chat(user_id=user.id, name='Study chat', local_id=1)
        db.add(chat)
        db.commit()
        db.refresh(chat)

        app = _make_app_with_db(db)

        from app.dependencies import get_current_user
        from app.schemas.user import UserResponse

        app.dependency_overrides[get_current_user] = lambda: UserResponse(id=user.id, name=user.name, email=user.email, token_limit=user.token_limit, tokens_used=user.tokens_used)

        created_tasks = []

        class FakeBackgroundTasks:
            def add_task(self, fn, task_id, use_ocr):
                created_tasks.append((fn, task_id, use_ocr))

        monkeypatch.setattr('app.routers.documents.BackgroundTasks', FakeBackgroundTasks, raising=False)

        client = TestClient(app)
        response = client.post(
            f'/documents/ingest/direct?user_id={user.id}&chat_id={chat.id}',
            files=[
                ('files', ('file1.pdf', b'%PDF-1', 'application/pdf')),
                ('files', ('file2.pdf', b'%PDF-2', 'application/pdf')),
            ],
        )

        assert response.status_code == 200
        assert response.json()['status'] == 'pending'
        assert db.query(IngestionTask).count() == 2
        assert {task.filename for task in db.query(IngestionTask).all()} == {'file1.pdf', 'file2.pdf'}
    finally:
        db.close()
