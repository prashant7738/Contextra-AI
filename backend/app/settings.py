from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = ""
    hf_token: str = ""
    chroma_persist_dir: str = "./my_vector_db"
    chroma_collection_name: str = "knowledge-base"

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
