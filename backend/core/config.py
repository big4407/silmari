"""
실마리(Silmari) 전역 설정 — .env 와 1:1 매핑되는 단일 Settings.

[발표 포인트] DB·JWT·외부 API 키·파일 경로가 모두 여기서 관리됨.
             Docker compose는 DB_HOST=db 등을 환경변수로 덮어씀.
"""

from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# core/config.py -> backend -> 프로젝트 루트
BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    # --- 앱 / 환경 ---
    app_name: str = "Silmari API"
    environment: str = "development"

    # --- DB (MySQL) ---
    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_NAME: str = "silmari"
    DB_USER: str = "root"
    DB_PASSWORD: str = ""
    DB_CHARSET: str = "utf8mb4"

    # --- DB (Chroma DB) ---
    chroma_dir: Path = PROJECT_ROOT / "data" / "chroma"

    # 로컬 개발 시 SQLite 등으로 강제 override 하고 싶을 때만 사용
    DATABASE_URL_OVERRIDE: str | None = None

    # --- 재난문자 API ---
    DISASTER_API_BASE_URL: str = ""
    DISASTER_API_PATH: str = ""
    DISASTER_API_SERVICE_KEY: str = ""

    # --- 외부 API 키 (utils/config.py 에서 흡수) ---
    SAFE182_API_KEY: str | None = None
    SAFE182_ESNTL_ID: str | None = None
    # SAFETYDATA_SERVICE_KEY 없으면 YOUR_API_KEY 로 폴백
    SAFETYDATA_SERVICE_KEY: str | None = Field(
        default=None,
        validation_alias=AliasChoices("SAFETYDATA_SERVICE_KEY", "YOUR_API_KEY"),
    )
    SAFETYDATA_API_URL: str = "https://www.safetydata.go.kr/V2/api/DSSP-IF-00247"

    # --- 파일 경로 (기본값 유지 + .env 로 override 가능) ---
    upload_dir: Path = PROJECT_ROOT / "data" / "uploads"
    yolo_model_path: Path = PROJECT_ROOT / "data" / "yolo" / "yolov8n.pt"
    cctv_data_dir: Path = PROJECT_ROOT / "data" / "CCTV"
    results_dir: Path = PROJECT_ROOT / "data" / "results"

    # --- JWT / 인증 (MemberSettings에서 흡수) ---
    jwt_secret_key: str = Field(
        default="replace-me-in-production-with-a-long-random-secret",
        min_length=32,
    )
    jwt_algorithm: str = "HS256"
    jwt_issuer: str = "silmari-auth"
    jwt_audience: str = "silmari-api"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # --- bootstrap admin ---
    bootstrap_admin_username: str | None = None
    bootstrap_admin_email: str | None = None
    bootstrap_admin_password: str | None = None
    bootstrap_admin_no_password: bool = False

    openai_api_key: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def database_url(self) -> str:
        if self.DATABASE_URL_OVERRIDE:
            return self.DATABASE_URL_OVERRIDE
        return (
            f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
            f"?charset={self.DB_CHARSET}"
        )

    @property
    def disaster_api_url(self) -> str:
        return f"{self.DISASTER_API_BASE_URL}{self.DISASTER_API_PATH}"

    @field_validator("SAFETYDATA_API_URL")
    @classmethod
    def _normalize_safetydata_url(cls, v: str) -> str:
        # 쿼리스트링 제거 + 상대경로면 host 보정
        if v and "?" in v:
            v = v.split("?")[0]
        if v and not v.startswith("http"):
            v = f"https://www.safetydata.go.kr{v}"
        return v

    @model_validator(mode="after")
    def validate_dev_bootstrap(self) -> "Settings":
        self.environment = self.environment.strip().lower()
        if self.bootstrap_admin_no_password:
            if self.environment not in {"development", "test"}:
                raise ValueError(
                    "BOOTSTRAP_ADMIN_NO_PASSWORD는 development/test에서만 사용 가능합니다."
                )
            if self.bootstrap_admin_password:
                raise ValueError(
                    "no_password 모드에서는 BOOTSTRAP_ADMIN_PASSWORD를 비워두세요."
                )
            if not (self.bootstrap_admin_username and self.bootstrap_admin_email):
                raise ValueError(
                    "no_password bootstrap에는 username/email이 필요합니다."
                )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


# 기존 `from backend.core.config import settings` 호환용
settings = get_settings()
