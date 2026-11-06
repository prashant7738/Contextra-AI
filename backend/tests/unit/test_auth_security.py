from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.core import rate_limit
from app.core.rate_limit import InMemoryRateLimiter, client_ip
from app.schemas.auth import UserLogin
from app.schemas.user import UserCreate
from app.services.storage_service import _safe_object_name


def _request(headers: dict, host: str = "10.0.0.1"):
    return SimpleNamespace(headers={k.lower(): v for k, v in headers.items()}, client=SimpleNamespace(host=host))


def test_limiter_blocks_after_max_and_sets_retry_after():
    limiter = InMemoryRateLimiter(max_requests=2, window_seconds=60)
    limiter.check("k")
    limiter.check("k")
    with pytest.raises(HTTPException) as exc:
        limiter.check("k")
    assert exc.value.status_code == 429
    assert int(exc.value.headers["Retry-After"]) >= 1
    limiter.check("other")  # keys are independent


def test_limiter_memory_is_bounded():
    limiter = InMemoryRateLimiter(max_requests=5, window_seconds=60, max_keys=50)
    for i in range(500):
        limiter.check(f"ip-{i}")
    assert len(limiter._hits) <= 50


def test_client_ip_prefers_edge_header_over_spoofable_forwarded_for():
    req = _request({"CF-Connecting-IP": "1.2.3.4", "X-Forwarded-For": "6.6.6.6, 1.2.3.4"})
    assert client_ip(req) == "1.2.3.4"
    assert client_ip(_request({"X-Forwarded-For": "5.5.5.5, 10.1.1.1"})) == "5.5.5.5"
    assert client_ip(_request({})) == "10.0.0.1"


def test_login_email_limiter_ignores_case_and_rotating_ips():
    rate_limit.reset_all_limiters()
    try:
        for _ in range(10):
            rate_limit.rate_limit_login_email("Victim@Example.com")
        with pytest.raises(HTTPException):
            rate_limit.rate_limit_login_email(" victim@example.com ")
    finally:
        rate_limit.reset_all_limiters()


def test_register_schema_normalizes_and_validates_email():
    user = UserCreate(name="  Ann ", email="  Ann@Example.COM ", password="password123")
    assert user.email == "ann@example.com"
    assert user.name == "Ann"
    for bad in ["not-an-email", "a@b", "a b@c.com"]:
        with pytest.raises(ValidationError):
            UserCreate(name="Ann", email=bad, password="password123")
    with pytest.raises(ValidationError):
        UserCreate(name="   ", email="a@b.com", password="password123")


def test_login_schema_normalizes_email():
    assert UserLogin(email=" Bob@X.io", password="x").email == "bob@x.io"


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("notes.pdf", "notes.pdf"),
        ("../../etc/passwd.pdf", "passwd.pdf"),
        ("..\\..\\win.pdf", "win.pdf"),
        ("my lecture (1).pdf", "my_lecture_1_.pdf"),
        ("", "file.pdf"),
    ],
)
def test_safe_object_name(raw, expected):
    assert _safe_object_name(raw) == expected
