# 실마리 (Silmari)

CCTV 기반 실종자 자동 탐지 시스템. 실종 안내문자에서 인상착의를 파싱하고, CCTV 영상에서 해당 인물을 매칭·추적하며, 수사관·행정담당자용 웹 인터페이스로 검색·사건관리·이력조회를 제공합니다.

- **Frontend** — React + Vite, Zustand, react-router-dom, Leaflet
- **Backend** — FastAPI, JWT 기반 RBAC 인증
- **Vision/ML** — YOLOv8(인물 탐지) + FashionCLIP(의류 속성) + torchreid(재식별)
- **DB** — MySQL 8 (SQLAlchemy 2.0)

---

## 프로젝트 구조

```
Silmari/
├── backend/
│   ├── main.py            # FastAPI 진입점 (lifespan에서 테이블 생성·admin bootstrap)
│   ├── deps.py            # 인증 의존성 (get_current_user, require_roles 등)
│   ├── Dockerfile
│   ├── routes/            # 모든 라우터 (auth, users, admin, operations,
│   │                      #              alert, cctv, result, disaster_alerts, messages)
│   ├── schemas/           # 모든 Pydantic 스키마 (auth, user, message, alert)
│   ├── db/
│   │   ├── database.py    # 단일 Base / engine / SessionLocal / get_db
│   │   ├── models.py      # 모든 ORM 모델 (User, AuthSession, Detection, SearchResult, Message)
│   │   └── crud.py        # 탐지·검색결과 CRUD
│   ├── repositories/      # 메시지 리포지토리
│   ├── services/          # 비즈니스 로직 + 외부 API 클라이언트
│   │   ├── auth_service.py
│   │   ├── cctv_reader.py
│   │   ├── message_service.py
│   │   ├── storage.py
│   │   ├── sms_receiver.py
│   │   ├── safetydata_client.py        # 재난안전데이터 API
│   │   └── disaster_message_client.py  # 재난문자 API
│   ├── core/
│   │   ├── config.py      # 단일 설정 (Settings) — DB·JWT·경로·외부키 전부
│   │   ├── security.py    # 비밀번호 해시·JWT
│   │   ├── runtime.py     # 파이썬 버전 체크
│   │   ├── pipeline.py    # 탐지 파이프라인 오케스트레이션
│   │   ├── vision/        # YOLO · FashionCLIP · 매칭
│   │   └── llm/           # 안내문자 파싱 체인
│   ├── utils/             # 순수 헬퍼 (logger, datetime_parser, timeutils, message_filter)
│   └── tests/
├── frontend/              # React + Vite (public/geodata 에 행정구역 데이터)
├── data/
│   ├── yolo/              # YOLO 가중치 (yolov8n.pt)
│   ├── CCTV/              # 입력 영상
│   ├── uploads/           # 업로드 파일
│   └── results/           # 탐지 결과·클립·썸네일
├── scripts/               # 인증 스모크 테스트 스크립트
├── fashionclip-taxonomy.md   # 의류 속성 분류 기준 레퍼런스
├── .env.example
├── docker-compose.yml
└── requirements.txt
```

**레이어 구성**: 라우터(`routes/`) · 인증 의존성(`deps.py`) · 스키마(`schemas/`)가 HTTP 계층,
`services/`가 비즈니스 로직·외부 연동, `db/`가 데이터, `core/`가 설정·보안·ML 엔진,
`utils/`가 프레임워크-비의존 순수 헬퍼입니다. **모든 설정은 `core/config.py` 한 곳**에 모여 있습니다.

> 비전(torch) 스택과 face/TF 스택은 의존성이 충돌하므로 환경을 분리해 운영하는 것을 권장합니다.

---

## 빠른 시작

### 1. 사전 준비

- Python 3.10
- Node.js 18+
- MySQL 8 (또는 docker-compose 사용)

### 2. 환경 변수

루트에 `.env`를 만듭니다(`.env.example` 복사). 백엔드를 **루트에서** 실행하면 이 파일을 읽습니다.

```bash
cp .env.example .env   # 값 채우기
```

`.env.example`의 모든 항목은 `core/config.py`의 `Settings` 필드와 매핑됩니다. 핵심만:

| 변수                                                               | 설명                                           |
| ------------------------------------------------------------------ | ---------------------------------------------- |
| `DB_HOST` / `DB_PORT` / `DB_NAME` / `DB_USER` / `DB_PASSWORD`      | MySQL 접속 정보                                |
| `DATABASE_URL_OVERRIDE`                                            | (선택) 로컬에서 SQLite 등으로 강제 지정 시     |
| `JWT_SECRET_KEY`                                                   | 32자 이상 무작위 값                            |
| `BOOTSTRAP_ADMIN_*`                                                | 최초 관리자 계정 (개발용은 `NO_PASSWORD=true`) |
| `SAFE182_*`, `SAFETYDATA_*`, `DISASTER_API_*`                      | 외부 재난·실종 API 키                          |
| `UPLOAD_DIR` / `YOLO_MODEL_PATH` / `CCTV_DATA_DIR` / `RESULTS_DIR` | (선택) 파일 경로. 미지정 시 루트 기준 기본값   |

> 파일 경로 4개는 기본값이 있어 보통 생략합니다(미지정 시 `data/yolo/`, `data/CCTV/` 등).
> **로컬 실행 시 `DB_HOST=localhost`**, Docker 실행 시에는 compose가 자동으로 `DB_HOST=db`로 덮어씁니다.

### 3. 백엔드 (로컬)

```bash
# 프로젝트 루트에서 실행 (backend 폴더 안 아님 — 절대 import 사용)
python -m venv .venv
.venv\Scripts\activate                 # Windows / (source .venv/bin/activate)
pip install -r requirements.txt

uvicorn backend.main:app --reload
```

- API: http://localhost:8000
- Swagger: http://localhost:8000/docs
- Health: http://localhost:8000/health

> `torchreid`는 git 소스 설치라 빌드가 오래 걸립니다. `requirements.txt`에서 해당 줄을 잠시 주석 처리해
> 나머지를 먼저 설치한 뒤 아래로 별도 설치할 수 있습니다.
>
> ```bash
> pip install --no-build-isolation "git+https://github.com/KaiyangZhou/deep-person-reid.git@f8cd150fdf77e8d9e1ed143b7f308c2c609ded50"
> ```

### 4. 프론트엔드 (로컬)

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173
```

### 5. Docker로 한 번에 (db + backend + frontend)

루트에 `.env`가 있고(아래 값 채움) `data/yolo/yolov8n.pt`가 있으면:

```bash
docker compose up --build
```

`db`(MySQL) → `backend`(8000) → `frontend`(5173) 순으로 기동합니다.

- 빌드 컨텍스트가 루트이므로 컨테이너 안에서도 `backend` 패키지가 그대로 import됩니다.
- `backend` 서비스는 compose의 `environment`로 **`DB_HOST=db`** 를 주입하므로,
  `.env`의 `localhost`(로컬용)와 충돌 없이 컨테이너에서는 `db` 서비스에 연결됩니다.
- `db` 서비스는 `${DB_PASSWORD}`·`${DB_NAME}`을 **루트 `.env`**에서 읽습니다.
- YOLO 가중치·데이터는 `./data` 볼륨으로 연결됩니다(`data/yolo/yolov8n.pt`).

설정 변경(예: `DB_HOST`) 후에는 기존 컨테이너를 지우고 다시 만들어야 반영됩니다:

```bash
docker compose down
docker compose up
```

---

## API 엔드포인트 (요약)

### 인증 / 사용자 (`/api/v1`)

| 경로                                | 설명                                  |
| ----------------------------------- | ------------------------------------- |
| `POST /auth/signup`                 | 회원가입 신청 (승인 상태 `pending`)   |
| `POST /auth/login`                  | 승인된 계정만 access/refresh JWT 발급 |
| `POST /auth/logout`                 | 세션 철회로 토큰 즉시 무효화          |
| `GET /users/me` · `PATCH /users/me` | 내 정보 조회·수정                     |
| `PATCH /admin/users/{id}/approval`  | 관리자 승인·반려·정지 및 역할 부여    |
| `GET /operations/case-search`       | `investigator` 역할 전용 예시         |

### 탐지 / 데이터

| 경로                     | 설명                                      |
| ------------------------ | ----------------------------------------- |
| `POST /api/alert/parse`  | 안내문자 인상착의 파싱                    |
| `POST /api/cctv/analyze` | CCTV 영상 분석 (탐지·클립 생성·결과 저장) |
| `GET /api/result/...`    | 탐지/검색 결과 조회·삭제                  |
| `GET /api/alerts/...`    | 재난문자 목록                             |
| `/messages/...`          | 메시지 수집·조회                          |

전체 스펙은 `/docs`(Swagger)에서 확인하세요.

---

## 프론트엔드 라우트

| 경로                 | 화면                       |
| -------------------- | -------------------------- |
| `/`                  | 랜딩                       |
| `/login`, `/signup`  | 로그인·회원가입            |
| `/dashboard`         | 대시보드 (지도 + 인상착의) |
| `/dashboard/chatbot` | 챗봇                       |
| `/dashboard/history` | 검색 이력                  |
| `/search-results`    | 탐지 결과                  |
| `/cctv`              | CCTV 영상 업로드           |

(`/alert` → `/cctv`, `/result` → `/search-results` 로 리다이렉트)

행정구역 지도 데이터는 `frontend/public/geodata/`에 있습니다(상세는 해당 폴더의 README 참고).

---

## 인증 모듈 (RBAC)

승인 기반 인증 모듈입니다. 회원가입 신청 → 관리자 승인 → JWT 로그인/로그아웃, 역할 기반 접근 제어(RBAC), 세션 철회를 지원합니다. 인증 의존성은 `backend/deps.py`에, 인증 로직은 `backend/services/auth_service.py`에 있습니다.

**개발용 bootstrap 관리자** — `.env`에 `ENVIRONMENT=development`(또는 `test`)와 `BOOTSTRAP_ADMIN_NO_PASSWORD=true`를 두면, 최초 관리자에게 무작위 비밀번호가 저장되고 로컬에서 아래로 관리자 JWT를 받을 수 있습니다. 운영 환경에서는 설정 검증 단계에서 차단됩니다.

```
POST /api/v1/auth/dev/bootstrap-login
```

**역할 보호 예시** — 라우트마다 허용 역할을 다르게 지정:

```python
from backend.deps import require_roles
from backend.db.models import User, UserRole

@router.get("/case-search")
def case_search(current_user: User = Depends(require_roles(UserRole.INVESTIGATOR))):
    ...
```

---

## 테스트

```bash
# 프로젝트 루트에서
python -m pytest backend/tests/ -q
```

> 루트에서 그냥 `pytest`로 돌리려면 루트에 `pyproject.toml`을 추가하고 `[tool.pytest.ini_options]`에
> `pythonpath = ["."]`를 설정하세요. (없으면 `backend` 패키지를 못 찾습니다.)
>
> 인증 테스트가 SQLite 테스트 DB를 쓰려면, `core/config.py`의 `DATABASE_URL_OVERRIDE`에
> `validation_alias="DATABASE_URL"`을 달거나, 테스트에서 `DATABASE_URL_OVERRIDE` 키로 주입해야 합니다.

인증 전체 흐름 스모크 테스트(서버 실행 후 별도 창):

```bash
python scripts/smoke_test_auth.py
# 또는 PowerShell: .\scripts\run_auth_smoke_test.ps1
```

---

## 운영 전 체크리스트

- `ENVIRONMENT=production`, `BOOTSTRAP_ADMIN_NO_PASSWORD=false`
- 관리자 비밀번호·`JWT_SECRET_KEY`를 강한 무작위 값으로
- CORS `allow_origins`를 실제 도메인으로 제한 (현재 `["*"]`)
- HTTPS, 로그인 rate limit, 감사 로그, Alembic 마이그레이션 도입
- `.env`·DB 파일·대용량 모델 가중치를 Git에 올리지 않도록 `.gitignore` 점검

---

## 참고 문서

- [FashionCLIP 의류 속성 분류 기준](fashionclip-taxonomy.md)
- 행정구역 지도 데이터: `frontend/public/geodata/README.md`
