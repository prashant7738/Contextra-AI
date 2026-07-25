import secrets

from fastapi import APIRouter, Header, HTTPException, status

from app.settings import settings

router = APIRouter(prefix="/cron", tags=["cron"])


@router.post("/run")
def run_cron_job(x_cron_secret: str | None = Header(default=None)):
    if not settings.cron_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Cron endpoint not configured",
        )

    if not x_cron_secret or not secrets.compare_digest(x_cron_secret, settings.cron_secret):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid cron secret")

    return {
        "ok": True,
        "job": "maintenance",
    }