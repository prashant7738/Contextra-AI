from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = ""
    hf_token: str = ""
    chroma_persist_dir: str = "./my_vector_db"
    chroma_collection_name: str = "knowledge-base"
    
    # JWT Configuration
    secret_key: str = "your-secret-key-change-this-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
