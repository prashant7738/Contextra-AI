import logging
import os
import tempfile
import uuid

import httpx

from app.settings import settings

logger = logging.getLogger(__name__)


def is_supabase_configured() -> bool:
    return bool(settings.supabase_url and settings.supabase_service_role_key)


def create_upload_presigned_url(filename: str) -> tuple[str, str]:
    if not is_supabase_configured():
        raise RuntimeError(
            "Supabase Storage not configured. Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY."
        )
    return _supabase_presign(filename)


def download_file(object_path: str) -> str:
    if is_supabase_configured():
        return _supabase_download(object_path)
    return object_path


def cleanup_temp_file(file_path: str) -> None:
    try:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
    except Exception as e:
        logger.warning(f"Failed to remove temp file {file_path}: {e}")


def _supabase_presign(filename: str) -> tuple[str, str]:
    bucket = settings.supabase_storage_bucket
    object_path = f"uploads/{uuid.uuid4().hex}_{filename}"

    url = f"{settings.supabase_url}/storage/v1/object/sign/{bucket}/{object_path}"
    headers = {
        "Authorization": f"Bearer {settings.supabase_service_role_key}",
        "Content-Type": "application/json",
    }

    resp = httpx.post(url, headers=headers, json={"upsert": True}, timeout=30)
    resp.raise_for_status()
    result = resp.json()
    upload_url = result.get("signedURL") or result.get("url") or result.get("signedUrl")

    if not upload_url:
        logger.error(f"Supabase signed upload response missing URL: {result}")
        raise RuntimeError("Failed to get signed upload URL from Supabase")

    if upload_url.startswith("/"):
        upload_url = f"{settings.supabase_url}{upload_url}"

    logger.info(f"Signed upload URL created for {object_path}")
    return upload_url, object_path


def _supabase_download(object_path: str) -> str:
    bucket = settings.supabase_storage_bucket
    url = f"{settings.supabase_url}/storage/v1/object/{bucket}/{object_path}"
    headers = {
        "Authorization": f"Bearer {settings.supabase_service_role_key}",
    }

    resp = httpx.get(url, headers=headers, timeout=120)
    resp.raise_for_status()

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf", prefix="ingest_")
    try:
        tmp.write(resp.content)
        tmp_path = tmp.name
    finally:
        tmp.close()

    logger.info(f"Downloaded {object_path} to {tmp_path}")
    return tmp_path
