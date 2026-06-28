from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = ""
    hf_token: str = ""
    admin_email: str = ""

    # Supabase Storage (leave empty to keep using direct upload)
    supabase_url: str = ""
    supabase_service_role_key: str = ""
    supabase_storage_bucket: str = "documents"

    # Embedding provider: "local", "openai", "huggingface"
    embedding_provider: str = "local"
    openai_api_key: str = ""

    # JWT Configuration
    secret_key: str = "your-secret-key-change-this-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
