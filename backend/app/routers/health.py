import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.database import SessionLocal

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


@router.get("/health")
@router.head("/health")
async def health():
    """Cheap liveness check for uptime monitors - never touches DB or LLM providers."""
    return {"status": "healthy"}


@router.get("/health/ready")
def readiness():
    """Readiness check: verifies the database answers a trivial query."""
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
    except Exception:
        logger.exception("Readiness check failed")
        return JSONResponse(status_code=503, content={"status": "unavailable", "database": "down"})
    return {"status": "ready", "database": "up"}
