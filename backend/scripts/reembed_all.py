"""Re-embed stored chunks with the current OpenAI embedding model.

Run from the backend directory after switching away from the old BGE embeddings:

    python -m scripts.reembed_all

Safe to stop and re-run: migrated rows are stamped with the model name in
chunk_metadata and skipped next time. Spend counts against the global daily
budget, so if the cap is hit the script stops and can be resumed the next UTC day.
"""
from fastapi import HTTPException
from sqlalchemy import select

from app.core.embeddings import EMBEDDING_MODEL, embed_texts
from app.database import SessionLocal, engine
from app.models.daily_spend import DailySpend
from app.models.embedding import Embedding

BATCH_SIZE = 100


def main() -> None:
    # The budget ledger table is normally created by the app on startup.
    DailySpend.__table__.create(bind=engine, checkfirst=True)
    migrated = 0
    db = SessionLocal()
    try:
        while True:
            rows = (
                db.execute(
                    select(Embedding)
                    .where(Embedding.chunk_metadata["embedding_model"].astext.is_distinct_from(EMBEDDING_MODEL))
                    .limit(BATCH_SIZE)
                )
                .scalars()
                .all()
            )
            if not rows:
                print(f"Done. Re-embedded {migrated} chunks.")
                return

            try:
                vectors = embed_texts([row.content for row in rows])
            except HTTPException as exc:
                print(f"Stopped after {migrated} chunks: {exc.detail} Re-run later to resume.")
                return

            for row, vector in zip(rows, vectors):
                row.embedding = vector
                row.chunk_metadata = {**(row.chunk_metadata or {}), "embedding_model": EMBEDDING_MODEL}
            db.commit()
            migrated += len(rows)
            print(f"Re-embedded {migrated} chunks so far...")
    finally:
        db.close()


if __name__ == "__main__":
    main()
