from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database import engine, Base
from app.routers import users, documents, chat


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("App Starting : Suiiiii")
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="Second Brain AI Workspace", lifespan=lifespan)

app.include_router(users.router)
app.include_router(documents.router)
app.include_router(chat.router)


@app.get("/")
def root():
    return {"message": "Hello from Second Brain AI", "step": 2}
