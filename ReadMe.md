# 실마리 (Silmari)

CCTV 기반 실종자 자동 탐지·검색 시스템. 정부 재난·안전 안내문자를 자동 수집해 실종자 정보를 추출하고, 인상착의(문자 입력 또는 챗봇 대화)로 CCTV 영상 속 인물을 검색합니다. 검색으로 끝나지 않고 **실종자 관리(케이스 배정·상태 추적)**, **관리자 통계/감사/보존정책**까지 아우르는 수사관·행정담당자용 웹 시스템입니다.

- **Frontend** — React 18 + Vite, Zustand, react-router-dom, Leaflet(지도 드릴다운)
- **Backend** — FastAPI, JWT 기반 RBAC 인증, `router → service → repository` 3계층 구조
- **Vision/ML** — YOLOv8(인물 탐지) + FashionCLIP(의류 속성 임베딩·검색) + torchreid(재식별)
- **LLM** — `ChatOpenAI`(구조화 출력)로 안내문자 파싱 + LangGraph 기반 챗봇(슬롯 추출 → 지역/기간 검증 → 검색 실행)
- **DB** — MySQL 8(SQLAlchemy 2.0, `Base.metadata.create_all` — 마이그레이션 도구 없음) + ChromaDB(로컬 파일 기반 벡터 검색)
- **스케줄러** — APScheduler로 안내문자 수집·영상 인덱싱 매일 자동 실행

> ⚠️ 여러 팀원이 병렬로 작업 중이라 구조가 자주 바뀝니다. **실제 라우팅의 최종 진실은 항상 `backend/main.py`**, **실제 테이블 정의는 `backend/db/models.py`**를 기준으로 확인하세요. 이 문서는 그 시점의 스냅샷입니다.

---

## 목차

1. [프로젝트 구조](#프로젝트-구조)
2. [데이터 모델](#데이터-모델)
3. [빠른 시작](#빠른-시작)
4. [Docker로 실행하기](#docker로-실행하기)
5. [API 엔드포인트](#api-엔드포인트)
6. [프론트엔드 라우트 · 관리자 콘솔](#프론트엔드-라우트--관리자-콘솔)
7. [인증 (RBAC)](#인증-rbac)
8. [챗봇 (LangGraph)](#챗봇-langgraph)
9. [백그라운드 스케줄러](#백그라운드-스케줄러)
10. [테스트](#테스트)
11. [알려진 이슈 / 설계상 트레이드오프](#알려진-이슈--설계상-트레이드오프)
12. [운영 전 체크리스트](#운영-전-체크리스트)
13. [참고 문서](#참고-문서)

---

## 프로젝트 구조

```
Silmari/
├── backend/
│   ├── main.py                  # FastAPI 진입점 — 모든 라우터 prefix가 여기 한 곳에 모여있음
│   ├── deps.py                  # 인증 의존성 (get_current_user, require_roles)
│   ├── Dockerfile
│   ├── routers/                 # HTTP 계층 — 요청 검증 후 서비스 호출만 함, DB 직접 접근 없음
│   │   ├── auth.py             # 회원가입/로그인/로그아웃/토큰 재발급/계정찾기·비번재설정
│   │   ├── users.py            # 내 정보 조회·수정
│   │   ├── admin.py            # 회원 승인, 통계/보존정책/데이터정합성/행정구역 관리 등 — 가장 큼
│   │   ├── operations.py       # RBAC 데모 라우트 (investigator 전용)
│   │   ├── messages.py         # 재난문자 수집·파싱·수동입력·조회·실종자관리 케이스 추가
│   │   ├── search.py           # 검색 요청 CRUD (생성 시 분석까지 동기 실행)
│   │   ├── chatbot.py          # 챗봇 대화 (LangGraph 그래프 호출)
│   │   ├── llm_call.py         # LLM 호출 이력 조회(사용량 통계용)
│   │   ├── missing_person_cases.py  # 실종자 관리 케이스 CRUD·배정·완료처리
│   │   ├── stats.py            # 관리자 통계 4종 + CSV 내보내기
│   │   └── video.py            # 영상 처리 엔드포인트 — 현재 미구현 스텁(아래 "알려진 이슈")
│   ├── schemas/                 # Pydantic 스키마 (HTTP 요청/응답 전용, 라우터별 파일 분리)
│   ├── db/
│   │   ├── database.py         # Base / engine / SessionLocal / get_db / get_chromadb / delete_video_embeddings
│   │   └── models.py           # 모든 ORM 모델 (아래 "데이터 모델" 참고)
│   ├── repositories/            # DB 접근 전담 — 서비스는 이 계층을 통해서만 DB를 만짐
│   ├── services/                # 비즈니스 로직 — 전부 `__init__(self, db)` + `self.repository` 패턴
│   │   ├── auth_service.py             # 로그인/세션/토큰 회전/회원가입/계정찾기
│   │   ├── message_service.py          # 재난문자 수집·저장·실종자케이스 자동/수동 생성
│   │   ├── search_service.py           # 검색 요청 저장 + AnalysisService 동기 호출
│   │   ├── analysis_service.py         # 지역/기간 필터 → Chroma 검색 → AnalysisDetail 저장
│   │   ├── video_service.py            # 영상 인덱싱(YOLO+FashionCLIP) + Chroma 임베딩 검색
│   │   ├── missing_person_case_service.py  # 실종자 케이스 상태 전이(대기→진행중→완료)·배정
│   │   ├── chatbot_service.py          # 챗봇 세션 관리 + LangGraph 실행 + 역할별 응답 분기
│   │   ├── stats_service.py / stats_export_service.py  # 통계 4종 조회 + CSV 내보내기 이력
│   │   ├── retention_service.py        # 삭제·보존 정책 dry-run/실행 (Chroma 임베딩도 같이 정리)
│   │   ├── region_admin_service.py     # 행정구역 CSV import/export (administrative_dong.csv)
│   │   ├── llm_call_service.py         # LLM 호출 기록·집계(사용량/비용)
│   │   ├── integrity_service.py        # 데이터 정합성 점검 실행·이력
│   │   ├── admin_dashboard_service.py  # 관리자 대시보드 요약 카드
│   │   ├── cctv_coverage_service.py    # CCTV 커버리지 통계 — video_service와 의도적으로 분리
│   │   │                                 (무거운 ML 스택 로딩 없이 단순 DB 집계만 하기 위함)
│   │   └── audit_service.py            # 관리자 감사 로그 기록 (리포지토리 없이 직접 add+flush 하는 유일한 예외)
│   ├── core/                    # CRUD가 아닌 도메인 알고리즘·설정
│   │   ├── config.py            # 단일 설정(Settings) — DB·JWT·경로·외부 API 키 전부
│   │   ├── security.py          # 비밀번호 해시·JWT 발급/검증
│   │   ├── runtime.py           # Python 3.10+ 버전 체크
│   │   ├── scheduler.py         # APScheduler — 안내문자 수집·영상 인덱싱 매일 자동 실행
│   │   ├── search/               # clothing_query.py(인상착의→FashionCLIP 쿼리), color_matching.py
│   │   ├── llm/                  # alert_parser.py(안내문자→실종자정보 LLM 추출), clothing_translator.py
│   │   └── chatbot/               # LangGraph 그래프 정의
│   │       ├── graph.py         # 노드·엣지 구성 (extract_slots → validate_* → create_search)
│   │       ├── nodes.py         # 각 노드 구현
│   │       ├── prompts.py       # 슬롯 추출 시스템 프롬프트
│   │       ├── schemas.py       # ExtractedSearchSlots — LLM 구조화 출력 전용(내부용)
│   │       └── state.py         # LangGraph 상태(TypedDict)
│   ├── utils/                    # 프레임워크 비의존 순수 헬퍼 (timeutils, datetime_parser 등)
│   └── tests/                    # pytest + 수동 실행용 테스트 데이터 세팅 스크립트
├── frontend/                    # React + Vite
│   └── src/
│       ├── api/                   # client.js(인증 axios 인스턴스, API_BASE 하드코딩), chatbot_api.js
│       ├── pages/                  # Landing, Login, Signup, FindAccountPage, Dashboard,
│       │                           # ChatbotPage, SearchHistory, SearchResults,
│       │                           # CasesPage/CaseCreatePage(실종자 관리), admin/*(관리자 콘솔)
│       ├── components/             # DashboardLayout, MapDrilldown, AlertMessageCard,
│       │                           # ClipSequencePlayer, DetectionCandidateList 등
│       ├── store/                   # useDetectionStore (Zustand)
│       └── utils/                   # 지역·행정동 매칭 유틸
├── data/
│   ├── yolo/yolov8n.pt          # YOLO 가중치
│   ├── raw/administrative_dong.csv  # 행정동 CSV 원본 — region 테이블 시드 데이터
│   ├── chroma/                   # ChromaDB 영속 저장소 (settings.chroma_dir)
│   ├── CCTV/                     # 인덱싱 대상 영상 — region_code/YYYYMMDD/cctv_serial_no/*.mp4
│   └── results/                   # 프레임·크롭 등 인덱싱 중간 산출물
├── scripts/                      # 인증 스모크 테스트
├── fashionclip-taxonomy.md       # FashionCLIP 의류 속성(색상·종류) 분류 기준
├── .env.example
├── docker-compose.yml
└── requirements.txt
```

**레이어 원칙**

- `routers/`는 요청 검증 후 서비스 호출만 하고 DB를 직접 만지지 않습니다.
- `services/`는 비즈니스 로직을 담당하며 모두 `self.repository`를 통해서만 DB에 접근합니다(`audit_service.py`만 예외 — 호출 측 트랜잭션에 일부러 묶기 위해 리포지토리 없이 add+flush만 합니다).
- `repositories/`는 순수 DB 접근만 하고 비즈니스 판단을 하지 않습니다.
- `core/`는 CRUD가 아닌 도메인 알고리즘(FashionCLIP 쿼리 변환, LLM 파싱, LangGraph 워크플로우, 보안·설정)이 모이는 곳입니다.
- **의존성 격리**: `cctv_coverage_service.py`와 `video_service`의 lazy 로딩은 의도적으로 무거운 ML 스택(torch/YOLO/FashionCLIP/torchreid)이 단순 DB 조회 경로까지 끌려오지 않게 분리되어 있습니다. 새 기능을 추가할 때 이 경계를 허물지 않도록 주의하세요.

> `torch`(YOLO·FashionCLIP·torchreid)가 무거운 의존성이라 첫 실행 시 모델 로딩에 시간이 걸립니다. `HF_HUB_OFFLINE=true`(기본값)라 FashionCLIP 캐시가 로컬에 없는 완전히 새 환경에서는 최초 1회 `HF_HUB_OFFLINE=false`로 켜서 다운로드가 되게 해야 합니다.

---

## 데이터 모델

| 모델                                                     | 역할                                                                                     |
| -------------------------------------------------------- | ---------------------------------------------------------------------------------------- |
| `User` / `AuthSession` / `LoginHistory` / `AdminHistory` | 회원(관리자/수사관/공무원)·세션·로그인 이력·관리자 감사 로그                             |
| `Message`                                                | 재난·안전 안내문자 원문 (행정안전부 API 수집)                                            |
| `MissingPersonCase`                                      | 실종자 관리 케이스 — 안내문자 1건당 1케이스(자동) 또는 수동 등록. 상태: 대기→진행중→완료 |
| `ChatbotSession`                                         | 챗봇 대화 상태(JSON) — `session_id`로 조회, 로그인 사용자와 연결                         |
| `Region` / `RegionLegalDong`                             | 행정구역 코드 체계(시도/시군구/행정동) + 법정동 매핑. `administrative_dong.csv`로 시드   |
| `Video` / `VideoDetail`                                  | 인덱싱된 CCTV 영상과 영상 내 인물 출현 구간(타임스탬프·좌표·색상)                        |
| `Search`                                                 | 검색 요청 (문자/챗봇/자동, 인상착의·지역·기간)                                           |
| `Analysis` / `AnalysisDetail`                            | 검색 요청 1건의 실행 결과와 매칭 후보(영상·시각·좌표·유사도·색상 매칭률)                 |
| `RetentionPolicy`                                        | 데이터 유형별 보존 기간·만료 시 처리 방식(현재는 삭제만 지원)                            |
| `LlmCall`                                                | 모든 LLM 호출 기록(모델·토큰·지연시간·비용) — 사용량 통계·비용 추적용                    |
| `StatsExportLog`                                         | 관리자 통계 CSV 내보내기 이력                                                            |

**핵심 흐름**

1. **문자 수집**: 스케줄러가 매일 안내문자를 수집 → `MessageService`가 저장과 동시에 `MissingPersonCase`를 자동 생성(대기 상태, 이름/인상착의는 아직 안 채움 — LLM 비용 때문에 배치 시점엔 안 뽑음).
2. **검색 실행**: `Search` 생성 → `AnalysisService`가 동기적으로 인상착의를 FashionCLIP 쿼리로 변환 → 지역·기간으로 좁힌 영상들 안에서 Chroma 유사도 검색 → 임계치를 넘는 후보만 `AnalysisDetail`로 저장.
3. **케이스 처리**: 담당자가 `MissingPersonCase`를 열면 그때 `enrich_from_message`로 LLM 파싱(이름/성별/나이/인상착의) 1건만 수행 → 담당 배정(진행중) → 완료 처리.
4. **보존정책**: 만료된 `Video`(파일+행+임베딩), `Analysis`, `Search`, `Message`를 주기적으로 삭제. `Video` 삭제 시 Chroma 임베딩도 반드시 같이 지워야 함(안 그러면 `video.id` 재사용 시 엉뚱한 영상이 매칭되는 버그로 이어짐 — `delete_video_embeddings` 참고).

---

## 빠른 시작

### 1. 사전 준비

- Python 3.10
- Node.js 18+
- MySQL 8 (또는 아래 [Docker](#docker로-실행하기) 사용)
- OpenAI API 키 (챗봇·안내문자 파싱용 — 없으면 해당 기능이 실패합니다)

### 2. 환경 변수

루트에 `.env`를 만듭니다(`.env.example` 복사). 백엔드를 **루트에서** 실행하면 이 파일을 읽습니다.

```bash
cp .env.example .env   # 값 채우기
```

`.env.example`의 모든 항목은 `core/config.py`의 `Settings` 필드와 매핑됩니다. 핵심만:

| 변수                                                               | 설명                                                            |
| ------------------------------------------------------------------ | --------------------------------------------------------------- |
| `DB_HOST` / `DB_PORT` / `DB_NAME` / `DB_USER` / `DB_PASSWORD`      | MySQL 접속 정보                                                 |
| `DATABASE_URL_OVERRIDE`                                            | (선택) 로컬에서 SQLite 등으로 강제 지정 시                      |
| `JWT_SECRET_KEY`                                                   | 32자 이상 무작위 값                                             |
| `BOOTSTRAP_ADMIN_*`                                                | 최초 관리자 계정 (개발용은 `NO_PASSWORD=true`)                  |
| `OPENAI_API_KEY`                                                   | 챗봇·안내문자 LLM 파싱용 키 (`.env.example`엔 없음 — 직접 추가) |
| `SAFE182_*`, `SAFETYDATA_*`, `DISASTER_API_*`                      | 외부 재난·실종 API 키                                           |
| `UPLOAD_DIR` / `YOLO_MODEL_PATH` / `CCTV_DATA_DIR` / `RESULTS_DIR` | (선택) 파일 경로. 미지정 시 루트 기준 기본값(`data/...`)        |

**실종 안내문자(대시보드 「안내문자 조회」)** — 팀원 각자:

1. 프로젝트 **루트**에서 `cp .env.example .env` (이미 있으면 생략)
2. `.env`에 **`SAFETYDATA_SERVICE_KEY=`** ← [재난안전데이터공유플랫폼](https://www.safetydata.go.kr/) 발급 **서비스키 값** (팀 채널로 공유, Git 금지)
3. `SAFETYDATA_API_URL`은 기본값(`DSSP-IF-00247`) 그대로 두면 됨
4. API 발급 시 **본인 PC 공인 IP**를 유저 IP에 등록 (미등록 시 403/호출 실패)
5. 값 변경 후 **백엔드 재시작** (Settings 캐시 때문)

> `backend/.env`는 예시 템플릿일 뿐이며, 실제로 읽히는 파일은 **루트 `.env`** 입니다.
> **로컬 실행 시 `DB_HOST=localhost`**, Docker 실행 시에는 compose가 자동으로 `DB_HOST=db`로 덮어씁니다.

### 3. 백엔드 (로컬)

```bash
# 프로젝트 루트에서 실행 (backend 폴더 안 아님 — 절대 import 사용)
python -m venv .venv
.venv\Scripts\activate                 # Windows / (source .venv/bin/activate)

# --break-system-packages 필요할 수 있음(Windows 아니면 생략)
pip install -r requirements.txt
```

> `torchreid`는 PyPI에 없어서 `requirements.txt`엔 주석으로만 안내돼 있습니다. `numpy`/`Cython`/`torch`/`torchvision`이 먼저 설치된 뒤 별도로 설치하세요:
>
> ```bash
> pip install --no-build-isolation "git+https://github.com/KaiyangZhou/deep-person-reid.git@f8cd150fdf77e8d9e1ed143b7f308c2c609ded50"
> ```

```bash
uvicorn backend.main:app --reload
```

- API: http://localhost:8000
- Swagger: http://localhost:8000/docs
- Health: http://localhost:8000/health

첫 실행 시 `region` 테이블이 비어있으면 서버가 자동으로 `data/raw/administrative_dong.csv`를 읽어 채웁니다(아래 [테스트](#테스트) 참고 — `test_setup_environment.py`도 같은 동작을 함).

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

---

## Docker로 실행하기

`db`(MySQL 8) + `backend`(FastAPI) + `frontend`(Vite dev server) 3개 컨테이너를 `docker-compose.yml` 한 번으로 띄웁니다.

### 사전 준비

1. **`.env` 파일** — 루트에 있어야 합니다(위 [환경 변수](#2-환경-변수) 참고). `docker-compose.yml`이 `env_file: [.env]`로 백엔드 컨테이너에 그대로 주입합니다.
2. **YOLO 가중치** — `data/yolo/yolov8n.pt`가 있어야 합니다(`./data`가 볼륨으로 컨테이너에 마운트됨).
3. Docker Desktop(Windows/Mac) 또는 Docker Engine + Compose plugin이 설치돼 있어야 합니다.

### 실행

```bash
docker compose up --build
```

- `db` → `backend` → `frontend` 순으로 기동합니다(`depends_on` + `db`의 healthcheck로 MySQL이 준비될 때까지 backend가 대기).
- 빌드 컨텍스트가 프로젝트 **루트**이므로(`backend/Dockerfile`을 루트에서 빌드) 컨테이너 안에서도 `backend` 패키지가 그대로 절대 import됩니다.
- `backend` 서비스는 compose의 `environment`로 **`DB_HOST=db`** 를 주입하므로, `.env`의 `localhost`(로컬 실행용 값)와 충돌 없이 컨테이너에서는 `db` 서비스 이름으로 접속합니다.
- `db` 서비스는 `${DB_PASSWORD}`·`${DB_NAME}`을 **루트 `.env`**에서 읽어 MySQL 루트 계정/DB를 초기화합니다. `docker-compose.yml`에서 서버 collation을 `utf8mb4_unicode_ci`로 명시적으로 맞춰뒀습니다(팀원마다 로컬 MySQL/MariaDB 기본 collation이 달라서 생기는 버그를 피하기 위함 — 네이티브 설치로 개발하는 사람은 이 collation을 직접 맞춰야 같은 문제를 안 겪습니다).
- YOLO 가중치·CCTV 영상·ChromaDB 저장소는 전부 `./data` 볼륨으로 컨테이너와 공유됩니다 — 컨테이너를 지워도 `data/` 안의 실제 데이터(영상, 인덱싱 결과, 벡터DB)는 호스트에 남습니다.

기동 후 접속:

- API: http://localhost:8000 (Swagger: `/docs`)
- Frontend: http://localhost:5173
- MySQL: `localhost:3306` (호스트에서 직접 붙어볼 때만 필요 — DB 클라이언트로 확인용)

### 백그라운드로 띄우기 / 로그 보기

```bash
docker compose up -d --build   # 백그라운드
docker compose logs -f backend # 백엔드 로그만 실시간
docker compose logs -f         # 전체 로그
```

### 재시작 / 설정 변경 반영

`.env` 값을 바꾼 뒤에는(예: `DB_PASSWORD`, API 키) 컨테이너를 내렸다가 다시 올려야 반영됩니다. `up`만 다시 하면 이미 떠 있는 컨테이너에 옛 값이 남아있을 수 있습니다.

```bash
docker compose down
docker compose up --build
```

### 완전 초기화 (DB 볼륨까지 삭제)

로컬 MySQL 데이터를 통째로 리셋하고 싶을 때(예: 스키마 꼬임, 테스트 데이터 정리):

```bash
docker compose down -v   # -v가 mysql_data 볼륨까지 삭제
docker compose up --build
```

> ⚠️ `-v`는 MySQL 데이터를 완전히 지웁니다. 다만 `./data`(YOLO 가중치, CCTV 영상, **ChromaDB**)는 볼륨 마운트가 아니라 바인드 마운트라 이 명령으로는 안 지워집니다. MySQL의 `video`/`video_detail` 등을 지운 뒤 ChromaDB를 안 같이 지우면, 나중에 `video.id`가 재사용될 때 예전 임베딩이 새 영상과 잘못 매칭되는 버그가 날 수 있습니다 — DB를 리셋했다면 `rm -rf data/chroma`도 같이 해주세요(또는 `python -m backend.tests.test_setup_environment --clear-existing-videos`로 앱을 통해 정리 — 아래 [테스트](#테스트) 참고).

### 컨테이너 안에서 직접 명령 실행

```bash
docker compose exec backend bash
docker compose exec db mysql -u root -p
```

### 자주 겪는 문제

| 증상                                                      | 원인 / 해결                                                                                                                                                                   |
| --------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| backend가 `db` 접속 대기하다 타임아웃                     | `.env`의 `DB_PASSWORD`가 `docker-compose.yml`의 `${DB_PASSWORD}`와 실제로 일치하는지 확인(빈 값이면 MySQL 초기화가 이상하게 될 수 있음)                                       |
| backend 빌드가 torchreid 설치 단계에서 오래 걸리거나 실패 | 정상 — git 소스 빌드라 몇 분 걸립니다. 계속 실패하면 `build-essential`/그래픽 라이브러리 관련 apt 캐시 문제일 수 있음, `docker compose build --no-cache backend`로 재시도     |
| YOLO 관련 `FileNotFoundError`                             | `data/yolo/yolov8n.pt`가 실제로 있는지, `./data`가 컨테이너에 제대로 마운트됐는지(`docker compose config`로 확인)                                                             |
| MariaDB 12.2+에서 `stats_export_log` 등 테이블 생성 실패  | `docker-compose.yml`의 `mysql:8.0` 이미지를 쓰면 안 겪는 문제입니다. 로컬에 네이티브로 최신 MariaDB를 깐 경우에만 해당(`to_date` 등 일부 컬럼명이 최신 MariaDB 예약어와 충돌) |

---

## API 엔드포인트

**prefix 원칙**: 모든 경로 prefix는 `backend/main.py`에서만 선언합니다. 각 라우터 파일(`routers/*.py`)은 자체 prefix를 갖지 않거나(`chatbot`, `messages`, `search`, `video`) 자체 prefix를 갖는 경우(`admin` → `/admin`, `auth` → `/auth`, `users` → `/users`, `stats` → `/admin/stats`)가 있고, `main.py`의 `include_router(..., prefix=...)`와 합쳐져 최종 경로가 됩니다. 전체 스펙은 `/docs`(Swagger)에서 확인하세요.

### 인증 · 회원 (`/member/auth`, `/member/users`)

| 경로                                    | 설명                                          |
| --------------------------------------- | --------------------------------------------- |
| `POST /member/auth/signup`              | 회원가입 신청 (승인 대기)                     |
| `POST /member/auth/find-username`       | 아이디 찾기                                   |
| `POST /member/auth/verify-identity`     | 본인 확인                                     |
| `POST /member/auth/reset-password`      | 비밀번호 재설정                               |
| `POST /member/auth/login`               | 승인된 계정만 access/refresh JWT 발급         |
| `POST /member/auth/refresh`             | refresh 토큰으로 access 토큰 재발급           |
| `POST /member/auth/logout`              | 세션 철회 — 즉시 토큰 무효화                  |
| `POST /member/auth/dev/bootstrap-login` | (개발 전용) bootstrap 관리자 테스트 토큰 발급 |
| `GET/PATCH /member/users/me`            | 내 정보 조회·수정                             |

### 관리자 (`/member/admin`)

| 경로                                                                                                  | 설명                                            |
| ----------------------------------------------------------------------------------------------------- | ----------------------------------------------- |
| `GET /member/admin/dashboard-summary`                                                                 | 관리자 대시보드 요약 카드                       |
| `GET /member/admin/users` · `PATCH .../users/{id}/approval`                                           | 회원 승인/반려/정지                             |
| `GET /member/admin/login-history` · `GET .../admin-history`                                           | 로그인·관리자 감사 로그                         |
| `GET /member/admin/search-requests`                                                                   | 검색 요청 이력                                  |
| `GET /member/admin/cctv-coverage` · `GET .../video-daily-summary`                                     | CCTV 커버리지·일별 영상 수집 현황               |
| `POST /member/admin/video-index-jobs/retry`                                                           | 영상 인덱싱 수동 재시도(스케줄러와 로직 공유)   |
| `GET/POST/PATCH/DELETE /member/admin/regions[...]`                                                    | 행정구역 조회/등록/수정/삭제, CSV import/export |
| `GET /member/admin/retention-policies` · `.../dry-run` · `.../execute` · `.../seed-defaults`          | 삭제·보존 정책 조회/시뮬레이션/실행/기본값 시드 |
| `POST /member/admin/data-integrity/run` · `GET .../last` · `GET .../runs/{id}` · `GET .../report.csv` | 데이터 정합성 점검 실행·이력·CSV                |

### 통계 (`/member/admin/stats`)

| 경로                                  | 설명                         |
| ------------------------------------- | ---------------------------- |
| `GET /member/admin/stats/cctv`        | CCTV 영상 통계               |
| `GET /member/admin/stats/search`      | 검색 통계                    |
| `GET /member/admin/stats/demographic` | 성별·연령·지역별 실종/검색율 |
| `GET /member/admin/stats/outcomes`    | 발견/해결 결과 통계          |
| `POST /member/admin/stats/export`     | 통계 CSV 내보내기            |
| `GET /member/admin/stats/exports`     | 내보내기 이력 목록           |

### 안내문자 (`/message`)

| 경로                                 | 설명                                                                |
| ------------------------------------ | ------------------------------------------------------------------- |
| `POST /message/collect`              | 외부 API에서 재난문자 수집 후 DB 저장 (스케줄러가 매일 자동 호출)   |
| `POST /message/parse`                | 안내문자 본문에서 LLM으로 실종자 정보(이름·성별·나이·인상착의) 추출 |
| `POST /message/manual_input`         | 문자 수동 등록                                                      |
| `POST /message/{sn}/case`            | 케이스 없는 문자를 실종자 관리에 backfill 등록 (관리자·수사관 전용) |
| `GET /message` · `GET /message/{sn}` | 문자 전체/단건 조회 (실종자 케이스 상태도 같이 내려줌)              |
| `DELETE /message/{sn}`               | 문자 삭제                                                           |

### 검색 (`/search`)

| 경로                         | 설명                                 |
| ---------------------------- | ------------------------------------ |
| `POST /search`               | 검색 요청 생성 (=분석까지 동기 실행) |
| `GET /search`                | 목록 조회                            |
| `GET /search/{search_id}`    | 단건 조회(영상별 매칭 결과 포함)     |
| `DELETE /search/{search_id}` | 삭제                                 |

### 챗봇 (`/chatbot`)

| 경로                                | 설명                                |
| ----------------------------------- | ----------------------------------- |
| `POST /chatbot/chat`                | 대화 1턴 (로그인 필요)              |
| `GET /chatbot/session`              | 세션 없으면 새로 발급 + 메시지 반환 |
| `GET /chatbot/session/{session_id}` | 세션 대화 이력 조회                 |
| `DELETE /chatbot/session`           | 현재 사용자 챗봇 세션 초기화        |

### 실종자 관리 (`/missing-person-cases`)

| 경로                                         | 설명                                              |
| -------------------------------------------- | ------------------------------------------------- |
| `GET /missing-person-cases`                  | 목록 조회 (상태·담당자·키워드 필터)               |
| `GET /missing-person-cases/{case_id}`        | 단건 조회                                         |
| `POST /missing-person-cases`                 | 수동 등록(챗봇 상담 등 안내문자에 안 묶인 케이스) |
| `POST .../{case_id}/assign` · `.../unassign` | 담당하기 / 담당 취소                              |
| `POST .../{case_id}/enrich`                  | 원문에서 LLM으로 이름/인상착의 등 채우기          |
| `POST .../{case_id}/resolve`                 | 완료 처리(되돌릴 수 없음)                         |
| `PATCH .../{case_id}/notes`                  | 메모 수정                                         |

### LLM 사용량 (`/llm_call`)

| 경로                                                              | 설명                                                 |
| ----------------------------------------------------------------- | ---------------------------------------------------- |
| `GET /llm_call/summary`                                           | 사용량 요약                                          |
| `GET /llm_call`                                                   | 목록 조회                                            |
| `GET /llm_call/admin`                                             | 관리자용 목록 — 문자 파싱은 건별, 챗봇은 세션별 집계 |
| `GET /llm_call/admin/message/{id}` · `.../chatbot/{chatbot_s_id}` | 상세 조회                                            |
| `GET/PATCH/DELETE /llm_call/{id}`                                 | 단건 조회/수정/삭제                                  |
| `GET /llm_call/detail/{id}`                                       | 상세                                                 |
| `POST /llm_call`                                                  | 수동 기록 생성                                       |

### 영상 (`/video`)

| 경로                  | 설명                                                                                                               |
| --------------------- | ------------------------------------------------------------------------------------------------------------------ |
| `POST /video/process` | **미구현 스텁** — 실제 인덱싱은 `VideoService`를 스케줄러/`video-index-jobs/retry`가 직접 호출(아래 "알려진 이슈") |

---

## 프론트엔드 라우트 · 관리자 콘솔

| 경로                   | 화면                                           |
| ---------------------- | ---------------------------------------------- |
| `/`                    | 랜딩                                           |
| `/login`, `/signup`    | 로그인·회원가입                                |
| `/find-account`        | 아이디 찾기·비밀번호 재설정                    |
| `/dashboard`           | 대시보드 (지도 + 인상착의 검색, 안내문자 목록) |
| `/dashboard/chatbot`   | 챗봇 검색                                      |
| `/dashboard/history`   | 검색 이력                                      |
| `/dashboard/cases`     | 실종자 관리 목록 (관리자·수사관 전용)          |
| `/dashboard/cases/new` | 실종자 케이스 수동 등록                        |
| `/search-results`      | 검색 결과 (영상 클립 재생 + 후보 타임라인)     |
| `/admin/:viewId`       | 관리자 콘솔 — 아래 참고                        |

`/alert`, `/cctv`, `/result`는 각각 `/dashboard`, `/dashboard`, `/search-results`로 리다이렉트됩니다. `/dashboard/*`는 `RequireAuth`, `/admin/*`는 `RequireAdmin` 가드로 보호됩니다.

**관리자 콘솔(`/admin/:viewId`)** — `frontend/src/pages/admin/navConfig.js` 기준 현재 탭 구성:

- **회원 관리**: 가입 승인 대기, 전체 회원
- **실종 안내문자**: 안내문자 목록
- **실종자 관리**: 실종사건 관리(배정·상태)
- **CCTV·검색 운영**: CCTV 영상 수집 현황, 검색 요청 이력
- **LLM 운영 관리**: LLM 사용량
- **통계**: CCTV/검색/성별·연령·지역/발견·해결 결과, 통계데이터 내보내기
- **데이터 관리**: 행정구역 관리, 데이터 정합성 점검, 삭제·보존 정책
- **감사 로그**: 관리자 활동, 승인·권한변경, 로그인·접근 이력

---

## 인증 (RBAC)

승인 기반 인증입니다. 회원가입 신청 → 관리자 승인 → JWT 로그인/로그아웃, 역할 기반 접근 제어, 세션 철회를 지원합니다. 의존성은 `backend/deps.py`, 로직은 `backend/services/auth_service.py`(`AuthService`)에 있습니다.

**역할 3종** (`UserRole`, DB엔 숫자 코드로 저장): `ADMIN("1")` 관리자, `INVESTIGATOR("2")` 수사관, `PUBLIC_OFFICIAL("3")` 공무원. 실종자 관리 시스템은 관리자·수사관 전용이며, 공무원 역할에는 관련 UI/챗봇 안내가 노출되지 않습니다.

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

챗봇(`POST /chatbot/chat`)도 `Depends(get_current_user)`로 보호되며, 로그인한 사용자의 실제 `user.id`와 `user.role`이 챗봇 세션·검색 요청·응답 분기(케이스 등록 제안 노출 여부)에 반영됩니다.

---

## 챗봇 (LangGraph)

`core/chatbot/`에 그래프 정의가 있습니다. 흐름: `extract_slots`(LLM으로 지역/시간/인상착의 추출) → `validate_region` → `validate_period` → `validate_appearance` → 슬롯이 부족하면 각 검증 노드가 되묻고, 다 채워지면 `create_search`로 실제 검색을 동기 실행합니다.

검색이 막 완료된 경우, 관리자·수사관 계정에는 "이 실종자를 실종자 관리 시스템에 케이스로 추가하시겠습니까?"를 함께 안내하고(`offer_case_registration: true`, `case_prefill`로 미리 채울 값 제공) 프론트가 추가하기/조회만 버튼을 보여줍니다. **공무원 계정에는 이 제안이 아예 노출되지 않습니다** — 실종자 관리 시스템 접근 권한이 없기 때문입니다.

**검색이 끝나면 세션을 정리합니다** — 안 그러면 같은 대화 세션에서 보내는 다음 메시지마다 이전 조건 그대로 매번 전체 파이프라인(LLM 호출 + FashionCLIP 임베딩 + Chroma 검색)이 다시 돌아갑니다. 프론트는 `chatbot_session_id`를 `localStorage`에 저장해 대화를 이어가므로, 완전히 새 대화로 시작하려면 브라우저에서 아래를 실행하고 새로고침하면 됩니다.

```js
localStorage.removeItem("chatbot_session_id");
```

---

## 백그라운드 스케줄러

`core/scheduler.py` — APScheduler(`AsyncIOScheduler`)가 두 작업을 매일 등록합니다.

| 작업                     | 시각(KST)      | 내용                                                                                        |
| ------------------------ | -------------- | ------------------------------------------------------------------------------------------- |
| `collect_messages_daily` | 매일 지정 시각 | `MessageService.collect_messages()` — 재난문자 API 수집·저장·케이스 자동 생성               |
| `process_videos_daily`   | 매일 지정 시각 | `VideoService.run_indexing_job(전날)` — 전날 CCTV 영상 인덱싱(YOLO+FashionCLIP+Chroma 저장) |

관리자 콘솔의 "인덱싱 재시도"(`POST /member/admin/video-index-jobs/retry`) 버튼도 같은 `run_indexing_job`을 호출합니다 — 스케줄러와 수동 재시도가 로직을 공유합니다.

---

## 테스트

```bash
# 프로젝트 루트에서
python -m pytest backend/tests/ -q
```

> 루트에서 그냥 `pytest`로 돌리려면 루트에 `pyproject.toml`을 추가하고 `[tool.pytest.ini_options]`에 `pythonpath = ["."]`를 설정하세요(현재 없음).

**로컬 테스트 데이터 한 번에 세팅** — 안내문자 삽입 → CCTV 폴더/영상 배치 → 실제 YOLO+FashionCLIP 인덱싱까지 한 번에 처리합니다. `region` 테이블이 비어있으면 `administrative_dong.csv`로 자동으로 먼저 채웁니다.

```bash
python -m backend.tests.test_setup_environment
python -m backend.tests.test_setup_environment --message-count 5 --max-videos 3
python -m backend.tests.test_setup_environment --region "대전광역시 동구 가양동" --clear-existing-messages

# 영상 관련 데이터(video/video_detail/analysis_detail) + Chroma 임베딩을 전부 지우고 재세팅
# — video엔 실제 운영 데이터와 구분하는 마커가 없어 테이블 전체가 지워짐, 운영 DB에서는 쓰지 말 것
python -m backend.tests.test_setup_environment --clear-existing-videos
```

인증 전체 흐름 스모크 테스트(서버 실행 후 별도 창):

```bash
python scripts/smoke_test_auth.py
# 또는 PowerShell: .\scripts\run_auth_smoke_test.ps1
```

---

## 알려진 이슈 / 설계상 트레이드오프

- **`routers/video.py`가 미구현 스텁** — 실제 YOLO/FashionCLIP 인덱싱 로직은 전부 `services/video_service.py`에 있고, 스케줄러(`process_videos_daily`)와 관리자 콘솔의 "인덱싱 재시도" 버튼이 그걸 직접 호출합니다. `POST /video/process`는 사실상 죽은 엔드포인트이며, 프론트에서도 이 경로를 호출하지 않습니다(`/cctv` 화면 자체가 `/dashboard`로 리다이렉트되도록 정리됨).
- **CORS** — `main.py`가 `allow_origins=["*"]` + `allow_credentials=True` 조합인데, 이 조합은 브라우저가 무효로 취급합니다. 운영 전에는 반드시 실제 프론트 도메인으로 좁히거나 `allow_origin_regex`를 써야 합니다.
- **마이그레이션 도구 없음** — `Base.metadata.create_all(bind=engine)`로 앱 시작 시 없는 테이블만 만듭니다. 컬럼 추가/변경은 반영이 안 되므로, 스키마를 바꿨다면 팀원들에게 알리고 로컬 DB를 직접 맞추거나(`ALTER TABLE`) 테이블을 지우고 재생성해야 합니다.
- **`Video`에 테스트/운영 데이터 구분 마커 없음** — `Message`는 `sn`에 `T` 접두어로 테스트 데이터를 안전하게 분리하는데, `Video`는 그런 장치가 없습니다(실제 CCTV와 같은 폴더 구조에 배치됨). `test_setup_environment.py --clear-existing-videos`는 그래서 `video` 테이블 전체를 지웁니다 — 운영 데이터가 섞인 환경에서는 절대 쓰지 마세요.
- **`video.id` 재사용과 ChromaDB 정합성** — `video.id`는 `AUTO_INCREMENT`인데, MySQL을 통째로 리셋(TRUNCATE/재생성)하면 카운터가 다시 시작될 수 있습니다. ChromaDB는 별도 로컬 파일 저장소라 MySQL 리셋에 안 딸려가므로, `Video` 행을 지울 때는 반드시 `delete_video_embeddings(video_id)`도 같이 호출해야 합니다(`retention_service.py`가 이미 그렇게 처리 — 새로 `Video`를 삭제하는 코드를 추가할 땐 이 패턴을 따르세요). **수동 SQL로 직접 지우는 경우는 이 보호를 안 타므로 각별히 주의**하세요.
- **로컬 MySQL/MariaDB 버전별 SQL 차이** — MariaDB 12.2+에서 `TO_DATE`가 새 예약어로 추가되어 특정 컬럼명이 충돌할 수 있고(→ DB 컬럼명을 `to_dt`/`from_dt`로 우회), `sql_mode=ONLY_FULL_GROUP_BY`(최신 MySQL/MariaDB 기본값) 위반 여부도 팀원 로컬 설정에 따라 다르게 나타날 수 있습니다. `docker-compose.yml`의 `mysql:8.0` 이미지를 쓰면 이런 환경 차이를 피할 수 있습니다.
- **챗봇의 지역/기간 파싱** — LLM이 추출한 값이 `validate_region_node`/`validate_period_node`에서 검증되지만, 지역명이 애매하면(`region` 테이블에 여러 후보가 매칭) 되묻는 흐름으로 처리됩니다.

---

## 운영 전 체크리스트

- `ENVIRONMENT=production`, `BOOTSTRAP_ADMIN_NO_PASSWORD=false`
- 관리자 비밀번호·`JWT_SECRET_KEY`를 강한 무작위 값으로
- CORS `allow_origins`를 실제 도메인으로 제한 (현재 `["*"]` — 위 "알려진 이슈" 참고)
- HTTPS, 로그인 rate limit, 감사 로그 점검
- Alembic 등 마이그레이션 도구 도입 (현재 `create_all` 기반이라 스키마 변경 이력 관리 안 됨)
- `.env`·DB 파일·대용량 모델 가중치·`data/chroma`를 Git에 올리지 않도록 `.gitignore` 점검
- 보존 정책(`retention_policy`)이 운영 환경 기준값으로 설정됐는지 확인

---

## 참고 문서

- [FashionCLIP 의류 속성 분류 기준](fashionclip-taxonomy.md)
- [변경 이력](CHANGELOG.md) — 초기 UI 개선 작업 기준, 이후 변경사항은 git log 참고
