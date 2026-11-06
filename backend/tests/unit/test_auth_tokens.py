from datetime import datetime, timedelta, timezone

import jwt

from app.core import auth
from app.settings import settings

# Produced by passlib's CryptContext(schemes=["bcrypt"]) before the migration
# to bcrypt directly: existing users must still be able to sign in.
PASSLIB_HASH = "$2b$12$pRBbdDaJ.Du19d0nleE4veSqg/2M3oawn/ZrGh1yhMS2lK1z8Lt32"
PASSLIB_HASH_LONG = "$2b$12$Deyf.oYZWLjI2HT7XNaqSerBzXWTDKsJtpCZZgMTyPDCUOsioHLs."  # 'L' * 100


def test_passlib_hashes_still_verify():
    assert auth.verify_password("correct horse battery", PASSLIB_HASH)
    assert not auth.verify_password("wrong", PASSLIB_HASH)
    # passlib truncated to 72 bytes silently; so do we.
    assert auth.verify_password("L" * 100, PASSLIB_HASH_LONG)


def test_hash_roundtrip_and_long_passwords():
    hashed = auth.hash_password("p" * 128)
    assert hashed.startswith("$2b$")
    assert auth.verify_password("p" * 128, hashed)
    assert not auth.verify_password("q" * 128, hashed)


def test_malformed_or_missing_hash_never_matches():
    assert not auth.verify_password("x", None)
    assert not auth.verify_password("x", "not-a-bcrypt-hash")


def test_access_token_roundtrip_and_type_check():
    token = auth.create_access_token({"sub": "7"})
    assert auth.verify_token(token, "access")["sub"] == "7"
    assert auth.verify_token(token, "refresh") is None


def test_refresh_token_carries_jti():
    exp = datetime.now(timezone.utc) + timedelta(days=1)
    token = auth.create_refresh_token({"sub": "7"}, jti="abc", expires_at=exp)
    payload = auth.verify_token(token, "refresh")
    assert payload["jti"] == "abc" and payload["sub"] == "7"


def test_rejects_expired_tampered_and_alg_none_tokens():
    expired = auth.create_access_token({"sub": "1"}, expires_delta=timedelta(seconds=-1))
    assert auth.verify_token(expired) is None
    other_key = jwt.encode({"sub": "1", "type": "access", "exp": datetime.now(timezone.utc) + timedelta(minutes=5)}, "k" * 40, algorithm="HS256")
    assert auth.verify_token(other_key) is None
    unsigned = jwt.encode({"sub": "1", "type": "access", "exp": datetime.now(timezone.utc) + timedelta(minutes=5)}, None, algorithm="none")
    assert auth.verify_token(unsigned) is None
    no_sub = jwt.encode({"type": "access", "exp": datetime.now(timezone.utc) + timedelta(minutes=5)}, settings.secret_key, algorithm="HS256")
    assert auth.verify_token(no_sub) is None
