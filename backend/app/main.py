import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import admin, auth, chat, cron, documents, health
from app.core import job_queue
from app.settings import settings

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Contextra AI backend")
    # Log only whether the key is present, never its value.
    logger.info("OpenAI API key present: %s", bool(settings.openai_api_key))
    # Schema is managed by Alembic (`alembic upgrade head` runs before start).
    # Ingestion and summary jobs are claimed from the database by these
    # workers; jobs interrupted by a restart are retried by the reaper.
    worker = job_queue.Worker(job_queue.worker_threads_from_env())
    worker.start()
    try:
        yield
    finally:
        worker.stop()


app = FastAPI(title="Contextra AI", lifespan=lifespan)

cors_origins = [
    origin.strip().rstrip("/")
    for origin in os.getenv("CORS_ORIGINS", "").split(",")
    if origin.strip()
]

# Must have explicit origins when allow_credentials=True (no wildcard "*")
if not cors_origins:
    cors_origins = ["http://localhost:3000", "http://localhost:4321", "https://contextra-ai.vercel.app"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(documents.router)
app.include_router(chat.router)
app.include_router(admin.router)
app.include_router(cron.router)
app.include_router(health.router)


@app.get("/")
def root():
    return {"message": "Hello from Contextra AI"}
