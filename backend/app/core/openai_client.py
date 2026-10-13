import openai
from openai import OpenAI

from app.settings import settings

_client: OpenAI | None = None


def get_openai_client() -> OpenAI:
    global _client
    if _client is None:
        if not settings.openai_api_key:
            raise RuntimeError("OpenAI API key not set. Set `OPENAI_API_KEY` in the environment or .env.")
        # No automatic retries: a retried call would be billed again outside our reservation.
        _client = OpenAI(api_key=settings.openai_api_key, max_retries=0, timeout=60)
    return _client


def is_unbilled_error(exc: Exception) -> bool:
    """True when the failed request certainly wasn't charged, so its reservation can be refunded."""
    if isinstance(exc, openai.APITimeoutError):
        return False  # may have been processed and billed
    if isinstance(exc, openai.APIConnectionError):
        return True
    return isinstance(exc, openai.APIStatusError) and exc.status_code < 500
