from functools import lru_cache

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    DB_HOST: str
    DB_PORT: int
    DB_NAME: str
    DB_USER: str
    DB_PASSWORD: str
    DB_CHARSET: str = "utf8mb4"

    DISASTER_API_BASE_URL: str
    DISASTER_API_PATH: str
    DISASTER_API_SERVICE_KEY: str

    @property
    def database_url(self) -> str:
        return (
            f"mysql+pymysql://"
            f"{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}"
            f"/{self.DB_NAME}"
            f"?charset={self.DB_CHARSET}"
        )

    @property
    def disaster_api_url(self) -> str:
        return f"{self.DISASTER_API_BASE_URL}{self.DISASTER_API_PATH}"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
