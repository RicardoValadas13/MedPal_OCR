from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # OpenAI credentials — set this in your .env file.
    openai_api_key: str = ""

    # Vision model used to read the prescription image and emit JSON.
    ocr_model: str = "gpt-4o"

    # Reject uploads larger than this (decoded bytes) to avoid huge payloads.
    max_image_bytes: int = 15 * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()
