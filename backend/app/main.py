from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database import engine, Base
from app.routers import users, documents, chat
from app.settings import settings
import os
import sys
try:
    import huggingface_hub
except Exception:
    huggingface_hub = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("App Starting : Suiiiii")
    # Log whether HF token is present (masked). Avoid printing the full token.
    print("HF token present:", bool(settings.hf_token))
    # Log common proxy env vars that can interfere with HTTP clients
    print("HTTP_PROXY:", os.environ.get("HTTP_PROXY") or os.environ.get("http_proxy"))
    print("HTTPS_PROXY:", os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy"))
    print("ALL_PROXY:", os.environ.get("ALL_PROXY") or os.environ.get("all_proxy"))
    # Log any HF-related env vars
    hf_envs = {k: v for k, v in os.environ.items() if k.startswith("HF_") or k.startswith("HUGGINGFACE")}
    print("HF-related env vars:", hf_envs)
    print("huggingface_hub version:", huggingface_hub.__version__ if huggingface_hub else "not installed")
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="Second Brain AI Workspace", lifespan=lifespan)

app.include_router(users.router)
app.include_router(documents.router)
app.include_router(chat.router)


@app.get("/")
def root():
    return {"message": "Hello from Second Brain AI", "step": 2}
