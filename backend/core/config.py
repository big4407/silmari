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
    image_save_dir: Path = PROJECT_ROOT / "data" / "results" / "unique_persons"
    frame_dir: Path = PROJECT_ROOT / "data" / "results" / "frames"
    detected_dir: Path = PROJECT_ROOT / "data" / "results" / "detected"
    administrative_dong_csv: Path = (
        PROJECT_ROOT / "data" / "raw" / "administrative_dong.csv"
    )

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

    # FashionCLIP 로드 시 huggingface_hub가 매번 "새 버전 있는지" 네트워크로
    # 확인하는 것(HEAD 요청)을 건너뛸지 여부. 캐시가 이미 있는 배포 환경에서는
    # 기본 True(오프라인)로 두는 게 맞다 — huggingface.co 접속이 느리거나
    # 막힌 환경에서 이 확인이 매번 타임아웃+재시도를 반복해 로딩이 멈춘
    # 것처럼 보이는 문제를 막는다. 캐시가 없는 새 환경에서 최초 다운로드가
    # 필요하면 .env에 HF_HUB_OFFLINE=false 로 잠깐 꺼두면 된다.
    hf_hub_offline: bool = True

    # huggingface_hub/transformers에 알려진 버그로, HF_HUB_OFFLINE=1이어도
    # 일부 코드 경로(특히 processor 로딩)가 최소 1번은 HEAD 요청을 시도한다
    # (huggingface/transformers #43200 등). 기본 타임아웃(10초)이 재시도 5번과
    # 겹치면 체감상 로딩이 멈춘 것처럼 보이므로, 이 요청 전용 타임아웃을
    # 짧게 줄여 실패를 빠르게 만든다 — huggingface.co 자체를 막는 게 아니라
    # (hosts 파일 차단과 달리 이 컴퓨터의 다른 프로그램은 영향 없음) 이
    # 프로세스의 존재-확인 요청만 빨리 포기하고 캐시로 넘어가게 한다.
    hf_hub_etag_timeout: int = 1

    # 검색 1건당 Chroma에서 가져오는 후보(AnalysisDetail) 최대 개수.
    # 프론트에서 페이지네이션으로 보여주므로 여기 값을 넉넉히 잡아도 화면이
    # 지저분해지지 않는다 — 다만 값이 크면 Chroma 조회·인덱싱 크기에 따라
    # 응답이 느려질 수 있어 .env에서 조정 가능하게 뺐다.
    search_result_limit: int = 100

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
        if self.DISASTER_API_BASE_URL and self.DISASTER_API_PATH:
            return f"{self.DISASTER_API_BASE_URL.rstrip('/')}{self.DISASTER_API_PATH}"
        return self.SAFETYDATA_API_URL

    @property
    def disaster_service_key(self) -> str:
        """재난안전데이터 API serviceKey — SAFETYDATA_* 우선, DISASTER_API_* 폴백."""
        return (self.SAFETYDATA_SERVICE_KEY or self.DISASTER_API_SERVICE_KEY or "").strip()

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