from pydantic import model_validator
from pydantic_settings import BaseSettings

MIN_SECRET_KEY_LENGTH = 32


class Settings(BaseSettings):
    database_url: str = ""
    admin_email: str = ""
    cron_secret: str = ""

    # Supabase Storage (leave empty to keep using direct upload)
    supabase_url: str = ""
    supabase_service_role_key: str = ""
    supabase_storage_bucket: str = "documents"

    openai_api_key: str = ""

    # Global daily spend cap across all users (UTC day), in USD
    daily_budget_usd: float = 0.25
    # gpt-6-luna and text-embedding-3-small prices, USD per 1M tokens
    llm_input_price_per_m: float = 0.10
    llm_cached_input_price_per_m: float = 0.01
    llm_output_price_per_m: float = 0.50
    embedding_price_per_m: float = 0.02

    # JWT Configuration
    secret_key: str = ""
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    default_user_token_limit: int = 25000

    model_config = {"env_file": ".env", "extra": "ignore"}

    @model_validator(mode="after")
    def _validate_secret_key(self) -> "Settings":
        """Fail fast at startup instead of silently signing JWTs with an empty/weak key."""
        if not self.secret_key or not self.secret_key.strip():
            raise ValueError(
                "SECRET_KEY is not set. Set a strong, random SECRET_KEY "
                "(e.g. `python -c \"import secrets; print(secrets.token_hex(32))\"`) "
                "in the environment or .env file before starting the app."
            )
        if len(self.secret_key) < MIN_SECRET_KEY_LENGTH:
            raise ValueError(
                f"SECRET_KEY is too short ({len(self.secret_key)} chars). "
                f"Use a random value of at least {MIN_SECRET_KEY_LENGTH} characters."
            )
        return self


settings = Settings()
