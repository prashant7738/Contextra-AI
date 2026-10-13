import pytest

from app.settings import Settings

SECRET = "x" * 32


@pytest.mark.parametrize(
    "raw",
    [
        "postgresql://user:pw@host:5432/db",
        "postgres://user:pw@host:5432/db",
        "postgresql+psycopg2://user:pw@host:5432/db",
    ],
)
def test_postgres_urls_are_pinned_to_psycopg2(raw):
    settings = Settings(database_url=raw, secret_key=SECRET)

    assert settings.database_url == "postgresql+psycopg2://user:pw@host:5432/db"


def test_other_driver_urls_are_left_alone():
    settings = Settings(database_url="postgresql+asyncpg://user:pw@host/db", secret_key=SECRET)

    assert settings.database_url == "postgresql+asyncpg://user:pw@host/db"
