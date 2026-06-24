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


class MemberSettings(BaseSettings):
    """Application settings loaded from environment variables or a local .env file."""

    app_name: str = "Silmari Auth API"
    environment: str = "development"

    # Example: mysql+pymysql://root:password@localhost:3307/silmari_auth?charset=utf8mb4
    database_url: str = "sqlite:///./silmari_auth.db"

    jwt_secret_key: str = Field(
        default="replace-me-in-production-with-a-long-random-secret",
        min_length=32,
    )
    jwt_algorithm: str = "HS256"
    jwt_issuer: str = "silmari-auth"
    jwt_audience: str = "silmari-api"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # The first administrator can be created at startup.
    bootstrap_admin_username: str | None = None
    bootstrap_admin_email: str | None = None
    bootstrap_admin_password: str | None = None

    # DEVELOPMENT / TEST ONLY.
    # When true, the bootstrap admin receives a random unknown password and can obtain a
    # local token through POST /api/v1/auth/dev/bootstrap-login. This is blocked outside
    # development and test environments.
    bootstrap_admin_no_password: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @model_validator(mode="after")
    def validate_development_bootstrap_mode(self) -> "Settings":
        self.environment = self.environment.strip().lower()

        if self.bootstrap_admin_no_password:
            if self.environment not in {"development", "test"}:
                raise ValueError(
                    "BOOTSTRAP_ADMIN_NO_PASSWORD는 development 또는 test 환경에서만 사용할 수 있습니다."
                )
            if self.bootstrap_admin_password:
                raise ValueError(
                    "BOOTSTRAP_ADMIN_NO_PASSWORD=true일 때 BOOTSTRAP_ADMIN_PASSWORD는 비워 두십시오."
                )
            if not self.bootstrap_admin_username or not self.bootstrap_admin_email:
                raise ValueError(
                    "비밀번호 없는 개발용 bootstrap을 사용하려면 BOOTSTRAP_ADMIN_USERNAME과 "
                    "BOOTSTRAP_ADMIN_EMAIL이 필요합니다."
                )

        return self


@lru_cache
def get_settings() -> MemberSettings:
    return MemberSettings()