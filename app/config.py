from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    database_url: str
    bright_data_api_key: str
    bright_data_serp_zone: str = "serp_api1"
    bright_data_unlocker_zone: str = "web_unlocker1"
    environment: str = "development"


@lru_cache
def get_settings() -> Settings:
    return Settings()
