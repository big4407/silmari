# 변경 이력 (Changelog)

`feat/frontend` 브랜치 및 최근 작업 정리입니다.

---

## [2026-06-26] — `feat/frontend` UI 개선

### Added

- **챗봇 검색 페이지 · UI 개선**
  - 메인 영역 전체 높이 사용 (중앙 떠 있는 640px 박스 제거)
  - 봇 아바타 + 좌/우 말풍선 구조 (봇: 연한 배경, 사용자: 네이비)
  - 추천 질문 칩 3개 (클릭 시 전송, FAQ 기반 답변)
  - 전송 버튼 네이비 + 화살표 아이콘, `tokens.css` 톤 통일
  - 메시지 추가 시 자동 스크롤

- **대시보드 · 문자 내용 검색**
  - 조회 조건에 `문자 내용` 입력란 추가 (예: `실종`, `홍길동`, `검은 점퍼`)
  - `안내문자 조회` 시 API `keyword` 파라미터로 전달 (`GET /api/alerts/list`)
  - Enter 키로도 조회 가능
  - Zustand 상태: `contentKeyword` / `setContentKeyword`

- **문서**
  - `CHANGELOG.md` 신규 (본 파일)
  - `ReadMe.md` 참고 문서에 CHANGELOG 링크 추가

### Changed

- **대시보드 · UX 1순위**
  - 시스템 에러(`API 키 또는 URL이 설정되지 않았습니다` 등)를 화면에 그대로 노출하지 않음
  - API 키·URL 미설정 → 안내형 빈 상태만 표시 (고장 난 사이트처럼 보이지 않게)
  - API 한도·일시 오류 → 빨간 `sidebar-error` 대신 `sidebar-notice` (경고/안내 톤)
  - 개발용 원문 에러는 브라우저 콘솔 `[alerts]` 로그만 출력
  - 지역 `지도 이동`: 빈 입력 시 에러 없음, **제출 후** 이름이 틀릴 때만 빨간 문구
  - 주요 버튼 색: 밝은 블루(`accent`) → 브랜드 네이비(`primary`) — `안내문자 조회`, `CCTV 분석`
  - `sidebar-hint` 왼쪽 강조선도 네이비로 통일

- **대시보드 · 빈 상태(empty state) 정리**
  - 「기본 조회 (최근 90일)」 띠 + 3단계 튜토리얼 + 빈 목록 영역이 겹치던 문제 해결
  - 결과 없을 때: 아이콘 + 제목 1줄 + 안내 1줄만 (점선 카드, 흰 배경)
  - 초기 문구: `표시할 안내문자가 없습니다` / `조건을 설정한 뒤 상단 「안내문자 조회」를 눌러 주세요.`
  - 조회 후 0건: `조건에 맞는 안내문자가 없습니다` 등 상황별 문구
  - 「기본 조회」 띠는 **결과가 있을 때만** 표시
  - `sidebar__body`로 빈 상태 / 목록 영역 분리 (이중 레이아웃 제거)

### 개발 시 참고 (프론트 수정)

| 방식 | 언제 쓰나 | 반영 속도 |
|------|-----------|-----------|
| `cd frontend && npm run dev` | UI·CSS·문구 수정 (권장) | 저장 시 자동 (HMR) |
| `docker compose up db backend` + 위 로컬 프론트 | API는 Docker, 화면만 로컬 | 즉시 |
| `docker compose up --build frontend` | Docker로 프론트만 배포형 확인 | **매번 이미지 빌드** (느림) |

→ **페이지 고칠 때마다 Docker 빌드할 필요 없음.** 평소엔 `npm run dev` 사용.

### 수정 파일

| 파일 | 내용 |
|------|------|
| `frontend/src/pages/ChatbotPage.jsx` | 챗봇 UI·칩·FAQ 매칭 |
| `frontend/src/pages/ChatbotPage.css` | 레이아웃·말풍선·네이비 버튼 |
| `frontend/src/pages/Dashboard.jsx` | 문자 검색, 에러 처리, 빈 상태, `hasSearched` |
| `frontend/src/pages/Dashboard.css` | 네이비 버튼, `sidebar-notice`, `sidebar__body`, 빈 상태 스타일 |
| `frontend/src/store/useDetectionStore.js` | `contentKeyword` |
| `CHANGELOG.md` | 변경 이력 |
| `ReadMe.md` | CHANGELOG 링크 |

---

## [2026-06-26] — main 머지

### Changed

- `main` → `feat/frontend` 머지 (`f8674f8`)
  - Docker 연동, `ReadMe.md` 정리, `backend/routes/` 구조 등 main 최신 반영
  - 충돌 해결: `matcher.py`, `frame_extractor.py`, `person_detector.py`
  - `feat/frontend`에서 제거된 얼굴인식 코드 유지
  - 삭제: `backend/api/schemas/result_schema.py`

### Note

- FashionCLIP XAI(유사도·히트맵) 작업은 별도 커밋 후 **되돌림** — main 머지만 유지

---

## [2026-06-26] — Docker 로컬 환경

### Added

- 루트 `.env` (`.env.example` 복사)
- `docker compose up --build` → `db` + `backend` + `frontend`

### 운영 메모

| 서비스 | URL |
|--------|-----|
| 프론트 | http://localhost:5173 |
| API / Swagger | http://localhost:8000/docs |
| MySQL | localhost:3306 |

- WSL 업데이트 후 Docker Desktop `Engine running` 확인 필요
- `localhost:5173`에 다른 Vite(hello-react 등)가 떠 있으면 실마리와 충돌 → 프로세스 종료 또는 `127.0.0.1:5173`

---

## 이전 `feat/frontend` 주요 커밋

| 커밋 | 요약 |
|------|------|
| `984dc38` | 얼굴인식·미사용 vision/auth 코드 제거 |
| `1502706` | main 병합 (지도 확대 프레임 등) |

---

## 앞으로 (예정, 미구현)

- 챗봇 백엔드: `/api/alerts/list` 등 실제 API·LangChain 에이전트 연동
- 대시보드 UX 2순위: 카드 레이아웃, 지도 톤·가이드 문구, 요약 통계
- Docker 프론트 소스 볼륨 마운트 (컨테이너에서도 HMR)
- FashionCLIP 본 파이프라인 + XAI 히트맵
- `SAFETYDATA_SERVICE_KEY` 설정 후 실제 안내문자 API 조회
