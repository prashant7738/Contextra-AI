import logging
import os
import re
import tempfile
import uuid

import httpx

from app.settings import settings

logger = logging.getLogger(__name__)

# Guard against unbounded downloads (e.g. a tampered/huge object) consuming
# excessive memory/disk during ingestion.
MAX_DOWNLOAD_SIZE_BYTES = 25 * 1024 * 1024  # 25 MB


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


def _safe_object_name(filename: str) -> str:
    """Keep only the basename with a conservative character set (no path traversal)."""
    base = os.path.basename((filename or "").replace("\\", "/"))
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", base).strip("._") or "file.pdf"
    return cleaned[:120]


def _supabase_presign(filename: str) -> tuple[str, str]:
    bucket = settings.supabase_storage_bucket
    object_path = f"uploads/{uuid.uuid4().hex}_{_safe_object_name(filename)}"

    url = f"{settings.supabase_url}/storage/v1/object/upload/sign/{bucket}/{object_path}"
    headers = {
        "Authorization": f"Bearer {settings.supabase_service_role_key}",
    }

    resp = httpx.post(url, headers=headers, timeout=30)
    resp.raise_for_status()
    result = resp.json()
    upload_url = result.get("url")

    # Never log the signed URL or response: they contain an upload token.
    if not upload_url:
        logger.error("Supabase signed upload response missing 'url' (keys: %s)", sorted(result))
        raise RuntimeError("Failed to get signed upload URL from Supabase")

    if upload_url.startswith("/"):
        upload_url = f"{settings.supabase_url.rstrip('/')}/storage/v1{upload_url}"

    logger.info("Signed upload URL created for %s", object_path)
    return upload_url, object_path


def _supabase_download(object_path: str) -> str:
    bucket = settings.supabase_storage_bucket
    url = f"{settings.supabase_url}/storage/v1/object/{bucket}/{object_path}"
    logger.info("Downloading %s from Supabase Storage", object_path)
    headers = {
        "Authorization": f"Bearer {settings.supabase_service_role_key}",
    }

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf", prefix="ingest_")
    tmp_path = tmp.name
    total = 0
    try:
        with httpx.stream("GET", url, headers=headers, timeout=120) as resp:
            resp.raise_for_status()
            for chunk in resp.iter_bytes(chunk_size=1024 * 1024):
                total += len(chunk)
                if total > MAX_DOWNLOAD_SIZE_BYTES:
                    raise RuntimeError(
                        f"Downloaded object exceeds maximum allowed size of "
                        f"{MAX_DOWNLOAD_SIZE_BYTES // (1024 * 1024)}MB"
                    )
                tmp.write(chunk)
    except Exception:
        logger.exception("Supabase download failed")
        tmp.close()
        cleanup_temp_file(tmp_path)
        raise
    finally:
        if not tmp.closed:
            tmp.close()

    logger.info(f"Downloaded {object_path} to {tmp_path}")
    return tmp_path
