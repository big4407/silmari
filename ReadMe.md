# 실마리 (Silmari)

CCTV 기반 실종자 자동 탐지·검색 시스템. 안내문자/챗봇으로 인상착의를 입력받아 FashionCLIP 임베딩으로 CCTV 영상 속 인물을 검색하고, 수사관·행정담당자용 웹 인터페이스로 검색·이력조회를 제공합니다.

- **Frontend** — React + Vite, Zustand, react-router-dom, Leaflet
- **Backend** — FastAPI, JWT 기반 RBAC 인증, `router → service → repository` 계층 구조
- **Vision/ML** — YOLOv8(인물 탐지) + FashionCLIP(의류 속성 임베딩·검색) + torchreid(재식별)
- **LLM** — LangGraph 기반 챗봇(인상착의 슬롯 추출 → 검색 실행)
- **DB** — MySQL 8(SQLAlchemy 2.0) + ChromaDB(벡터 검색)

> ⚠️ 이 문서는 `feat/dev` 브랜치의 현재 상태를 기준으로 작성되었습니다. 여러 팀원이 병렬로 작업 중이라 구조가 자주 바뀝니다 — 실제 라우팅은 항상 `backend/main.py`를 기준으로 확인하세요.

---

## 프로젝트 구조

```
Silmari/
├── backend/
│   ├── main.py               # FastAPI 진입점 — 모든 라우터 prefix가 여기 한 곳에 모여있음
│   ├── deps.py                # 인증 의존성 (get_current_user, get_current_session_id, require_roles)
│   ├── Dockerfile
│   ├── routers/                # HTTP 계층 — 요청 검증 후 서비스 호출만 함
│   │   ├── auth.py            # 회원가입·로그인·로그아웃·토큰 재발급
│   │   ├── users.py           # 내 정보 조회·수정
│   │   ├── admin.py           # 회원 승인/반려/정지, 로그인·관리자 감사이력
│   │   ├── operations.py      # RBAC 데모 라우트 (investigator 전용, 추후 정리 예정)
│   │   ├── messages.py        # 재난문자 수집·조회
│   │   ├── search.py          # 검색 요청 CRUD (생성 시 분석까지 동기 실행)
│   │   ├── chatbot.py         # 챗봇 대화 (LangGraph 그래프 호출)
│   │   └── video.py           # 영상 처리 — 현재 엔드포인트만 있고 내부 구현은 비어있는 스텁
│   ├── schemas/                 # Pydantic 스키마 (HTTP 요청/응답 전용, 라우터별로 파일 분리)
│   ├── db/
│   │   ├── database.py        # Base / engine / SessionLocal / get_db / get_chromadb
│   │   └── models.py          # 모든 ORM 모델 (아래 "데이터 모델" 참고)
│   ├── repositories/            # DB 접근 계층 — 서비스는 이 계층을 통해서만 DB를 만짐
│   │   ├── auth_repository.py      # User / AuthSession / LoginHistory
│   │   ├── audit_repository.py     # AdminHistory
│   │   ├── chatbot_repository.py   # ChatbotSession
│   │   ├── message_repository.py
│   │   ├── search_repository.py
│   │   ├── analysis_repository.py  # Analysis / AnalysisDetail
│   │   ├── region_repository.py    # 지역명 → region_code 조회
│   │   └── video_repository.py     # Video / VideoDetail
│   ├── services/                # 비즈니스 로직 — 전부 `__init__(self, db)` + `self.repository` 패턴
│   │   ├── auth_service.py         # 로그인/세션/토큰 회전/회원가입
│   │   ├── audit_service.py        # 관리자 감사 로그 기록
│   │   ├── message_service.py      # 재난문자 수집·저장
│   │   ├── search_service.py       # 검색 요청 저장 + AnalysisService 동기 호출
│   │   ├── analysis_service.py     # 지역/기간 필터 → Chroma 검색 → AnalysisDetail 저장
│   │   ├── video_service.py        # 영상 인덱싱(YOLO+FashionCLIP) + Chroma 임베딩 검색
│   │   └── chatbot_service.py      # 챗봇 세션 관리 + LangGraph 실행
│   ├── core/                    # CRUD가 아닌 도메인 알고리즘·설정 (서비스가 이 계층을 호출)
│   │   ├── config.py           # 단일 설정(Settings) — DB·JWT·경로·외부 API 키 전부
│   │   ├── security.py         # 비밀번호 해시·JWT 발급/검증
│   │   ├── runtime.py          # 파이썬 버전 체크
│   │   ├── scheduler.py        # APScheduler — 재난문자 수집·영상 인덱싱 주기 작업
│   │   ├── pipeline.py         # (레거시) 탐지 파이프라인 — 상당 부분 미완성/비어있음
│   │   ├── search/              # 인상착의(한글) → FashionCLIP 영문 쿼리 변환
│   │   ├── vision/               # 현재 비어있음 (YOLO/FashionCLIP 실행 코드는 services/video_service.py로 이동)
│   │   ├── llm/                  # 현재 비어있음
│   │   └── chatbot/              # LangGraph 그래프 정의 — CRUD가 아니라 워크플로우 엔진이라 core/ 소속
│   │       ├── graph.py         # 노드·엣지 구성 (extract_slots → validate → ask_missing / create_search)
│   │       ├── nodes.py         # 각 노드 구현 — DB 접근은 services/search_service.py만 거침
│   │       ├── prompts.py       # 슬롯 추출 시스템 프롬프트
│   │       ├── schemas.py       # ExtractedSearchSlots — LLM 구조화 출력 전용(내부용, HTTP 스키마 아님)
│   │       └── state.py         # LangGraph 상태(TypedDict)
│   ├── utils/                   # 프레임워크 비의존 순수 헬퍼 (logger, timeutils, datetime_parser 등)
│   └── tests/
├── frontend/                   # React + Vite
│   └── src/
│       ├── api/                  # client.js(인증 axios 인스턴스), chatbot_api.js
│       ├── pages/                 # Landing, Login, Signup, Dashboard, ChatbotPage,
│       │                          # SearchHistory, SearchResults, CCTVUpload, admin/*
│       ├── components/            # DashboardLayout, AppLayout, MapDrilldown,
│       │                          # DetectionCandidateList, SearchResultCard 등
│       ├── hooks/                  # useLogout, useMapDrilldown
│       ├── store/                  # useDetectionStore (Zustand)
│       └── utils/                  # 지역·행정동 매칭 유틸
├── data/
│   ├── yolo/yolov8n.pt         # YOLO 가중치
│   ├── CCTV/                   # 인덱싱 대상 영상 — region_code/YYYYMMDD/cctv_serial_no/*.mp4
│   ├── raw/                    # 행정동 CSV 등 원본 데이터
│   └── results/                 # 프레임·크롭 등 중간 산출물
├── scripts/                     # 인증 스모크 테스트
├── fashionclip-taxonomy.md      # FashionCLIP 의류 속성(색상·종류) 분류 기준
├── .env.example
├── docker-compose.yml
└── requirements.txt
```

**레이어 원칙**: `routers/`는 요청 검증 후 서비스 호출만 하고 DB를 직접 만지지 않습니다. `services/`는 비즈니스 로직을 담당하며 모두 `self.repository`를 통해서만 DB에 접근합니다(직접 `db.query()`/`db.add()`를 쓰지 않습니다 — `audit_service.py`만 예외로, 호출 측 트랜잭션에 일부러 묶기 위해 리포지토리 없이 add+flush만 합니다). `repositories/`는 순수 DB 접근만 하고 비즈니스 판단을 하지 않습니다. `core/`는 CRUD가 아닌 도메인 알고리즘(FashionCLIP 쿼리 변환, LangGraph 워크플로우, 보안·설정)이 모이는 곳입니다.

> `torch`(YOLO·FashionCLIP·torchreid)가 무거운 의존성이라 첫 실행 시 모델 로딩에 시간이 걸립니다.

---

## 데이터 모델 (핵심)

| 모델                                                     | 역할                                                             |
| -------------------------------------------------------- | ---------------------------------------------------------------- |
| `User` / `AuthSession` / `LoginHistory` / `AdminHistory` | 회원·세션·감사 로그                                              |
| `Message`                                                | 재난문자 원문                                                    |
| `ChatbotSession`                                         | 챗봇 대화 상태(JSON) — `session_id`로 조회, 로그인 사용자와 연결 |
| `Region`                                                 | 지역코드 체계 (현재 시드 데이터 없음 — 아래 "알려진 이슈" 참고)  |
| `Video` / `VideoDetail`                                  | 인덱싱된 CCTV 영상과 영상 내 인물 출현 구간                      |
| `Search`                                                 | 검색 요청 (SMS/챗봇/자동, 인상착의·지역·기간)                    |
| `Analysis` / `AnalysisDetail`                            | 검색 요청 1건의 실행 결과와 매칭 후보(영상·시각·좌표·유사도)     |

`Search` 생성 → `AnalysisService`가 동기적으로 인상착의를 FashionCLIP 쿼리로 변환 → 지역·기간으로 좁힌 영상들 안에서 Chroma 유사도 검색 → 임계치를 넘는 후보만 `AnalysisDetail`로 저장하는 흐름입니다.

---

## 빠른 시작

### 1. 사전 준비

- Python 3.10
- Node.js 18+
- MySQL 8 (또는 docker-compose 사용)
- OpenAI API 키 (챗봇용 — 없으면 챗봇 대화가 슬롯 추출 단계에서 실패합니다)

### 2. 환경 변수

루트에 `.env`를 만듭니다(`.env.example` 복사). 백엔드를 **루트에서** 실행하면 이 파일을 읽습니다.

```bash
cp .env.example .env   # 값 채우기
```

`.env.example`의 모든 항목은 `core/config.py`의 `Settings` 필드와 매핑됩니다. 핵심만:

| 변수                                                               | 설명                                                        |
| ------------------------------------------------------------------ | ----------------------------------------------------------- |
| `DB_HOST` / `DB_PORT` / `DB_NAME` / `DB_USER` / `DB_PASSWORD`      | MySQL 접속 정보                                             |
| `DATABASE_URL_OVERRIDE`                                            | (선택) 로컬에서 SQLite 등으로 강제 지정 시                  |
| `JWT_SECRET_KEY`                                                   | 32자 이상 무작위 값                                         |
| `BOOTSTRAP_ADMIN_*`                                                | 최초 관리자 계정 (개발용은 `NO_PASSWORD=true`)              |
| `OPENAI_API_KEY`                                                   | 챗봇 슬롯 추출용 LLM 키 (`.env.example`엔 없음 — 직접 추가) |
| `SAFE182_*`, `SAFETYDATA_*`, `DISASTER_API_*`                      | 외부 재난·실종 API 키                                       |

**실종 안내문자(대시보드 「안내문자 조회」)** — 팀원 각자:

1. 프로젝트 **루트**에서 `cp .env.example .env` (이미 있으면 생략)
2. `.env`에 **`SAFETYDATA_SERVICE_KEY=`** ← [재난안전데이터공유플랫폼](https://www.safetydata.go.kr/) 발급 **서비스키 값** (팀 채널로 공유, Git 금지)
3. `SAFETYDATA_API_URL`은 기본값(`DSSP-IF-00247`) 그대로 두면 됨
4. API 발급 시 **본인 PC 공인 IP**를 유저 IP에 등록 (미등록 시 403/호출 실패)
5. 값 변경 후 **백엔드 재시작** (`uvicorn` 재실행 — Settings 캐시 때문)

> `backend/.env`는 예시 템플릿일 뿐이며, 실제로 읽히는 파일은 **루트 `.env`** 입니다.
| `UPLOAD_DIR` / `YOLO_MODEL_PATH` / `CCTV_DATA_DIR` / `RESULTS_DIR` | (선택) 파일 경로. 미지정 시 루트 기준 기본값                |

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

> `torchreid`는 git 소스 설치라 `requirements.txt`엔 주석으로만 안내돼 있습니다. 나머지를 먼저 설치한 뒤 별도 설치하세요:
>
> ```bash
> pip install --no-build-isolation "git+https://github.com/KaiyangZhou/deep-person-reid.git@f8cd150fdf77e8d9e1ed143b7f308c2c609ded50"
> ```

> **Windows에서 서버를 재시작할 때는 이전 프로세스가 완전히 죽었는지 꼭 확인하세요.** `--reload`로 띄운 프로세스가 무거운 작업(모델 로딩 등) 중 강제 종료되면 포트 8000을 붙잡은 좀비 프로세스가 남아 새 요청이 응답 없이 계속 pending 되는 경우가 있습니다.
>
> ```bash
> netstat -ano | findstr :8000
> taskkill /F /PID <PID>
> ```

### 4. 프론트엔드 (로컬)

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173
```

프론트는 `http://localhost:8000`을 백엔드 주소로 하드코딩해서 사용합니다(`frontend/src/api/client.js`의 `API_BASE`).

### 5. Docker로 한 번에 (db + backend + frontend)

루트에 `.env`가 있고(아래 값 채움) `data/yolo/yolov8n.pt`가 있으면:

```bash
docker compose up --build
```

`db`(MySQL) → `backend`(8000) → `frontend`(5173) 순으로 기동합니다.

- 빌드 컨텍스트가 루트이므로 컨테이너 안에서도 `backend` 패키지가 그대로 import됩니다.
- `backend` 서비스는 compose의 `environment`로 **`DB_HOST=db`** 를 주입하므로, `.env`의 `localhost`(로컬용)와 충돌 없이 컨테이너에서는 `db` 서비스에 연결됩니다.
- `db` 서비스는 `${DB_PASSWORD}`·`${DB_NAME}`을 **루트 `.env`**에서 읽습니다.
- YOLO 가중치·데이터는 `./data` 볼륨으로 연결됩니다.

설정 변경(예: `DB_HOST`) 후에는 기존 컨테이너를 지우고 다시 만들어야 반영됩니다:

```bash
docker compose down
docker compose up
```

---

## API 엔드포인트

**prefix 원칙**: 모든 경로 prefix는 `backend/main.py`에서만 선언합니다. 각 라우터 파일(`routers/*.py`)은 자체 prefix를 갖지 않는 `APIRouter()`로 시작하고, `main.py`의 `include_router(..., prefix=...)` 호출만 보면 전체 API 구조를 알 수 있습니다.

| 경로                                                                                                                   | 설명                                                                   |
| ---------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------- |
| `POST /member/auth/signup`                                                                                             | 회원가입 신청 (승인 대기)                                              |
| `POST /member/auth/login`                                                                                              | 승인된 계정만 access/refresh JWT 발급                                  |
| `POST /member/auth/refresh`                                                                                            | refresh 토큰으로 access 토큰 재발급                                    |
| `POST /member/auth/logout`                                                                                             | 세션 철회 — 즉시 토큰 무효화                                           |
| `POST /member/auth/dev/bootstrap-login`                                                                                | (개발 전용) bootstrap 관리자 테스트 토큰 발급                          |
| `GET/PATCH /member/users/me`                                                                                           | 내 정보 조회·수정                                                      |
| `GET /member/admin/users` · `PATCH /member/admin/users/{id}/approval`                                                  | 회원 승인/반려/정지                                                    |
| `GET /member/admin/login-history` · `GET /member/admin/admin-history`                                                  | 감사 로그 조회                                                         |
| `GET /member/operations/case-search`                                                                                   | `investigator` 역할 전용 RBAC 데모(추후 제거 검토)                     |
| `POST /message/collect` · `POST /message/manual_input` · `GET /message` · `GET /message/{sn}` · `DELETE /message/{sn}` | 재난문자 수집·수동입력·조회·삭제                                       |
| `POST /search` · `GET /search` · `GET /search/{id}` · `DELETE /search/{id}`                                            | 검색 요청 생성(=분석까지 동기 실행)·목록·단건·삭제                     |
| `POST /chatbot/chat`                                                                                                   | 챗봇 대화 (로그인 필요)                                                |
| `POST /video/process`                                                                                                  | 영상 처리 — 엔드포인트만 있고 내부 구현은 비어있음(아래 "알려진 이슈") |

전체 스펙은 `/docs`(Swagger)에서 확인하세요.

---

## 프론트엔드 라우트

| 경로                 | 화면                                                                                |
| -------------------- | ----------------------------------------------------------------------------------- |
| `/`                  | 랜딩                                                                                |
| `/login`, `/signup`  | 로그인·회원가입                                                                     |
| `/dashboard`         | 대시보드 (지도 + 인상착의 검색)                                                     |
| `/dashboard/chatbot` | 챗봇 검색                                                                           |
| `/dashboard/history` | 검색 이력                                                                           |
| `/search-results`    | 검색 결과                                                                           |
| `/cctv`              | CCTV 영상 업로드 — 현재 백엔드 엔드포인트 미구현으로 동작 안 함(아래 "알려진 이슈") |
| `/admin/:viewId`     | 관리자 콘솔 (회원·감사 로그 등)                                                     |

(`/alert` → `/cctv`, `/result` → `/search-results` 로 리다이렉트)

---

## 인증 (RBAC)

승인 기반 인증입니다. 회원가입 신청 → 관리자 승인 → JWT 로그인/로그아웃, 역할 기반 접근 제어, 세션 철회를 지원합니다. 의존성은 `backend/deps.py`, 로직은 `backend/services/auth_service.py`(`AuthService`)에 있습니다.

**개발용 bootstrap 관리자** — `.env`에 `ENVIRONMENT=development`(또는 `test`)와 `BOOTSTRAP_ADMIN_NO_PASSWORD=true`를 두면, 최초 관리자에게 무작위 비밀번호가 저장되고 로컬에서 아래로 관리자 JWT를 받을 수 있습니다.

```
POST /member/auth/dev/bootstrap-login
```

**역할 보호 예시**:

```python
from backend.deps import require_roles
from backend.db.models import User, UserRole

@router.get("/case-search")
def case_search(current_user: User = Depends(require_roles(UserRole.INVESTIGATOR))):
    ...
```

챗봇(`POST /chatbot/chat`)도 `Depends(get_current_user)`로 보호되며, 로그인한 사용자의 실제 `user.id`가 챗봇 세션과 검색 요청에 연결됩니다(세션 ID 자체는 프론트가 발급하는 별개의 값).

---

## 챗봇 (LangGraph)

`core/chatbot/`에 그래프 정의가 있습니다. 흐름: `extract_slots`(LLM으로 지역/시간/인상착의 추출) → `validate_slots` → 슬롯이 부족하면 `ask_missing`으로 되묻고, 다 채워지면 `create_search`로 실제 검색을 동기 실행합니다.

**검색이 끝나면 슬롯을 자동으로 비웁니다** — 안 그러면 같은 대화 세션에서 보내는 다음 메시지마다 이전 조건 그대로 매번 전체 파이프라인(LLM 호출 + FashionCLIP 임베딩 + Chroma 검색)이 다시 돌아갑니다. 프론트는 `chatbot_session_id`를 `localStorage`에 저장해 대화를 이어가므로, 완전히 새 대화로 시작하려면 브라우저에서 아래를 실행하고 새로고침하면 됩니다.

```js
localStorage.removeItem("chatbot_session_id");
```

---

## 테스트

```bash
# 프로젝트 루트에서
python -m pytest backend/tests/ -q
```

> 루트에서 그냥 `pytest`로 돌리려면 루트에 `pyproject.toml`을 추가하고 `[tool.pytest.ini_options]`에 `pythonpath = ["."]`를 설정하세요.

인증 전체 흐름 스모크 테스트(서버 실행 후 별도 창):

```bash
python scripts/smoke_test_auth.py
# 또는 PowerShell: .\scripts\run_auth_smoke_test.ps1
```

---

## 알려진 이슈 / 진행 중

- **`Region` 시드 데이터 없음** — 지역명→region_code 조회(`RegionRepository.find_codes_by_keyword`)가 매칭 실패 시 지역 필터 없이 진행하도록 되어 있어 당장 에러는 안 나지만, 실제 지역 필터링을 쓰려면 `region` 테이블을 채우는 경로가 다시 필요합니다.
- **`routers/video.py`, `core/vision/`, `core/llm/`, `core/pipeline.py`** — 실제 YOLO/FashionCLIP 인덱싱 로직은 `services/video_service.py`로 옮겨갔고, 이 파일들은 대부분 비어있거나 스텁 상태입니다. 특히 `/cctv` 화면(`CCTVUpload.jsx`)이 호출하는 영상 업로드→분석 API가 지금 없어서 이 화면은 동작하지 않습니다 — `routers/video.py`를 채우는 게 이걸 되살리는 자연스러운 자리입니다.
- **CORS** — `main.py`가 `allow_origins=["*"]` + `allow_credentials=True` 조합인데, 이 조합은 브라우저가 무효로 취급합니다. 운영 전에는 반드시 실제 프론트 도메인으로 좁혀야 합니다.
- **챗봇의 `start_time`/`end_time`** — LLM이 추출한 시간대 정보가 아직 `Search.start_date`/`end_date`(실제 영상 검색 기간 필터)로 연결되지 않고 응답 문구에 참고용으로만 표시됩니다.

---

## 운영 전 체크리스트

- `ENVIRONMENT=production`, `BOOTSTRAP_ADMIN_NO_PASSWORD=false`
- 관리자 비밀번호·`JWT_SECRET_KEY`를 강한 무작위 값으로
- CORS `allow_origins`를 실제 도메인으로 제한 (현재 `["*"]` — 위 "알려진 이슈" 참고)
- HTTPS, 로그인 rate limit, 감사 로그, Alembic 마이그레이션 도입
- `.env`·DB 파일·대용량 모델 가중치를 Git에 올리지 않도록 `.gitignore` 점검

---

## 참고 문서

- [FashionCLIP 의류 속성 분류 기준](fashionclip-taxonomy.md)
