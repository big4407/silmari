# 실마리 — 미연결 코드 체크리스트 (이슈 티켓)

> 팀 공유용. "지워도 되나?" / "뭘 먼저 붙여야 하나?" 판단할 때 사용하세요.  
> 작성 기준: 2025-07 · `rg "파일명" .` 로 import 여부 재확인 권장.

---

## 우선순위 요약

| 우선순위 | 의미 | 건수 |
|----------|------|------|
| **P0** | 핵심 기능 연결 — 안 하면 제품이 동작 안 함 | 2 |
| **P1** | 프로덕션 화면 ↔ API 연결 | 4 |
| **P2** | 정리·삭제 후보 (지우기 전 import 재확인) | 7 |
| **P3** | dev/테스트 전용 — 운영 배포엔 불필요 | 유지 |

---

## P0 — 반드시 연결 (핵심 파이프라인)

### ISSUE-001 · CCTV 분석 API에 detect_missing_person_pipeline 연결

**상태:** `[ ]` 미완  
**유형:** CONNECT  
**담당 제안:** 백엔드 / 비전

**현상**
- `POST /api/cctv/analyze` → `run_detection_pipeline()` 호출
- `run_detection_pipeline()` 이 **deprecated 스텁** → 항상 `detections: []`, `total_detections: 0`
- 실제 비전 로직은 `detect_missing_person_pipeline()` 에 구현됨 (API 미연결)

**관련 파일**
```
backend/routers/cctv.py
backend/core/pipeline.py                    ← run_detection_pipeline (스텁), detect_missing_person_pipeline (구현)
backend/core/vision/crop_embedding.py
backend/core/vision/search_embedding.py
backend/core/vision/frame_extractor.py
backend/core/vision/person_detector.py
```

**작업**
- [ ] `run_detection_pipeline()` 에서 `detect_missing_person_pipeline()` 호출 또는 흡수
- [ ] `crop_embedding` / `search_embedding` 흐름이 DB·Chroma 저장과 맞는지 확인
- [ ] `POST /api/cctv/analyze`로 실제 탐지 1건 이상 나오는지 수동 테스트

**완료 조건**
- 영상 업로드 후 `detections` 배열에 후보가 1건 이상 반환됨
- `SearchResults` 화면에 클립/썸네일 표시됨

**검증**
```bash
rg "detect_missing_person_pipeline|run_detection_pipeline" backend/
```

---

### ISSUE-002 · 야간 인덱싱 / 당일 검색 파이프라인 연결

**상태:** `[ ]` 미완  
**유형:** CONNECT  
**담당 제안:** 백엔드 / 비전

**현상**
- `index_video_pipeline()` — Chroma `index_video()` 호출 **주석**
- `search_pipeline()` — `search_persons()` 호출 **주석**, `return ""`

**관련 파일**
```
backend/core/pipeline.py
backend/core/vision/crop_embedding.py
backend/core/vision/search_embedding.py
backend/db/crud.py                ← index_embeddings, search_embeddings
backend/tests/test_pipeline.py    ← 테스트만 부분 호출
```

**작업**
- [ ] `index_video_pipeline` 내 crop 임베딩·Chroma 저장 연결
- [ ] `search_pipeline` 내 `search_embedding` / Chroma 검색 연결 (`return []` 제거)
- [ ] 스케줄러 또는 수동 트리거로 인덱싱 실행 경로 정의
- [ ] `test_pipeline.py` 통과

**완료 조건**
- 인덱싱 후 Chroma에 임베딩 존재
- `search_pipeline(clothes_en=...)` 이 `list[MatchCandidate]` 반환

**검증**
```bash
python -m pytest backend/tests/test_pipeline.py -q
```

---

## P1 — 프로덕션 화면 ↔ API 연결

### ISSUE-003 · 로그인 / 회원가입 API 연동

**상태:** `[ ]` 미완  
**유형:** CONNECT  
**담당 제안:** 프론트엔드

**현상**
- `Login.jsx`, `Signup.jsx` — UI만, `onSubmit`이 `preventDefault()`만 함
- `auth_api.js` + `devClient.js`는 **`/dev/auth`에서만** 사용

**관련 파일**
```
frontend/src/pages/Login.jsx
frontend/src/pages/Signup.jsx
frontend/src/api/auth_api.js
frontend/src/api/devClient.js
backend/routers/auth.py
```

**작업**
- [ ] Login → `POST /api/auth/login`
- [ ] Signup → `POST /api/auth/signup`
- [ ] JWT 저장 방식 결정 (sessionStorage vs httpOnly cookie)
- [ ] `client.js`에 인증 헤더 인터셉터 추가
- [ ] 로그인 후 `/dashboard` 리다이렉트

**완료 조건**
- 메인 `/login`에서 승인된 계정으로 로그인 가능
- `/dev/auth` 없이도 인증 플로우 동작

---

### ISSUE-004 · 검색 이력 페이지 API 연동

**상태:** `[ ]` 미완  
**유형:** CONNECT  
**담당 제안:** 프론트엔드

**현상**
- `SearchHistory.jsx` — "준비 중입니다" 플레이스홀더
- 백엔드 `GET /api/detection-results/history` 존재하나 **프론트 미호출**

**관련 파일**
```
frontend/src/pages/SearchHistory.jsx
frontend/src/api/client.js
backend/routers/result.py
```

**작업**
- [ ] `client.js`에 `fetchDetectionHistory()` 추가
- [ ] `SearchHistory.jsx`에서 목록 렌더링
- [ ] 항목 클릭 시 `/search-results` 또는 상세로 이동

**완료 조건**
- `/dashboard/history`에서 과거 탐지 이력 표시

---

### ISSUE-005 · 안내문자 파싱을 프로덕션 화면에 연결

**상태:** `[ ]` 미완  
**유형:** CONNECT  
**담당 제안:** 프론트엔드

**현상**
- `POST /api/alerts/parse` — **DevAlertPage만** 호출
- Dashboard / CCTV 업로드에서 파싱 API 직접 호출 없음 (CCTV analyze 시 백엔드 내부 파싱만)

**관련 파일**
```
frontend/src/pages/dev/DevAlertPage.jsx
frontend/src/pages/Dashboard.jsx
frontend/src/pages/CCTVUpload.jsx
backend/routers/alert.py
```

**작업**
- [ ] (선택) Dashboard에서 안내문자 붙여넣기 → 파싱 미리보기 UI
- [ ] 파싱 결과를 `useDetectionStore`에 반영
- [ ] `client.js`에 `parseAlertText()` 추가

**완료 조건**
- 프로덕션 화면에서 파싱 API를 dev 없이 호출 가능 (또는 팀이 "CCTV analyze 내부만 쓴다"로 범위 축소 시 이슈 close)

---

### ISSUE-006 · Admin 콘솔 API 연동

**상태:** `[ ]` 미완  
**유형:** CONNECT  
**담당 제안:** 프론트엔드 / 백엔드

**현상**
- `frontend/src/pages/admin/views/*` — 20개 뷰 UI 껍데기
- `MemberViews.jsx` 등 주석: "/api/admin 연동 예정"
- 실제 API 호출 거의 없음

**관련 파일**
```
frontend/src/pages/admin/views/
frontend/src/pages/admin/navConfig.js
backend/routers/admin.py
```

**작업 (우선순위 내부)**
- [ ] `members-pending` → `GET/PATCH /api/admin/users`
- [ ] 나머지 뷰는 placeholder 유지 vs 제거 결정

**완료 조건**
- 최소 회원 승인 화면이 실제 admin API와 동작

---

## P2 — 삭제 / 통합 후보

> **규칙:** 삭제 전 반드시 `rg "파일명|export이름" .` 실행. import 0건 확인 후 PR.

### ISSUE-101 · `classify_video.py` 삭제

**상태:** `[ ]` 검토  
**유형:** DELETE  
**리스크:** 낮음

| 항목 | 내용 |
|------|------|
| 파일 | `backend/utils/classify_video.py` |
| 이유 | import 0건, 옛 절대경로 하드코딩, 실험 스크립트 |
| 대체 | 없음 (필요 시 `data/raw/administrative_dong.csv` 활용 스크립트 새로 작성) |

- [ ] `rg "classify_video" .` → 0건 확인
- [ ] 파일 삭제

---

### ISSUE-102 · `PersonCard` 컴포넌트 삭제

**상태:** `[ ]` 검토  
**유형:** DELETE  
**리스크:** 낮음

| 항목 | 내용 |
|------|------|
| 파일 | `frontend/src/components/PersonCard.jsx`, `PersonCard.css` |
| 이유 | import 0건 — 만들어 두고 미사용 |
| 대체 | `SearchResultCard.jsx` 사용 중 |

- [ ] `rg "PersonCard" frontend/` → 정의 파일만 남는지 확인
- [ ] 파일 삭제

---

### ISSUE-103 · `ChatbotWidget` 삭제 또는 ChatbotPage에 적용

**상태:** `[ ]` 검토  
**유형:** DELETE 또는 CONNECT  
**리스크:** 낮음

| 항목 | 내용 |
|------|------|
| 파일 | `frontend/src/components/ChatbotWidget.jsx`, `ChatbotWidget.css` |
| 이유 | `ChatbotPage.jsx`가 자체 인라인 UI 사용, Widget import 0건 |
| 선택 A | 삭제 |
| 선택 B | `ChatbotPage`에서 `ChatbotWidget` 사용하도록 리팩터 |

- [ ] 팀 결정: 삭제 vs 통합
- [ ] 실행

---

### ISSUE-104 · `search_missing_person.py` vs `search_embedding.py` 통합

**상태:** `[ ]` 검토  
**유형:** DELETE / MERGE  
**리스크:** 중간

| 항목 | 내용 |
|------|------|
| 파일 | `backend/core/vision/search_missing_person.py` |
| 이유 | import 0건, `search_embedding.py`와 역할 중복 |
| 사용 중 | `detect_missing_person_pipeline` → `search_embedding`만 사용 |

- [ ] `search_missing_person.py` 기능이 필요한지 비전 담당 확인
- [ ] 불필요 시 삭제, 필요 시 `detect_missing_person_pipeline`에 통합

---

### ISSUE-105 · `utils/logger.py` 사용 또는 삭제

**상태:** `[ ]` 검토  
**유형:** DELETE 또는 CONNECT  
**리스크:** 낮음

| 항목 | 내용 |
|------|------|
| 파일 | `backend/utils/logger.py` |
| 이유 | import 0건 |
| 선택 A | 삭제 |
| 선택 B | `main.py` 또는 서비스에서 `from backend.utils.logger import logger` 도입 |

---

### ISSUE-106 · `chatbot/prompts.py` 연결 또는 삭제

**상태:** `[ ]` 검토  
**유형:** DELETE 또는 CONNECT  
**리스크:** 낮음

| 항목 | 내용 |
|------|------|
| 파일 | `backend/chatbot/prompts.py` |
| 이유 | `SLOT_EXTRACTION_PROMPT` 정의만 있고 `nodes.py`에서 미사용 |
| 선택 A | `extract_slots_node`에 프롬프트 주입 |
| 선택 B | structured output만 쓸 거면 삭제 |

---

### ISSUE-107 · `detect_missing_person_pipeline` 정리

**상태:** `[ ]` 검토  
**유형:** MERGE into ISSUE-001  
**리스크:** 중간

| 항목 | 내용 |
|------|------|
| 파일 | `backend/core/pipeline.py` 내 함수 + vision 하위 모듈 일부 |
| 이유 | API 미연결, `if __name__` 직접 실행만 |
| 전용 모듈 | `frame_extract`, `person_detect`, `check_same_person`, `crop_embedding`, `search_embedding` |

**선택**
- [ ] A) `detect_missing_person_pipeline`을 `run_detection_pipeline`에 흡수 (권장)
- [ ] B) 별도 dev API (`POST /api/cctv/analyze-experimental`) 유지

---

## P3 — dev/테스트 전용 (삭제 불필요, 운영 배포 시 제외)

| 항목 | 경로 | 비고 |
|------|------|------|
| Dev API 허브 | `frontend/src/pages/dev/*` | `/dev/*` |
| Dev API 클라이언트 | `frontend/src/api/devClient.js` | sessionStorage JWT |
| Auth 스모크 테스트 | `scripts/smoke_test_auth.py` | |
| 백엔드 테스트 | `backend/tests/*` | |
| 챗봇 단독 테스트 | `backend/chatbot/chatbot_test.py` | |
| RBAC 데모 API | `GET /api/operations/case-search` | 테스트·dev만 |
| 레거시 API prefix | `main.py` 152–162행 | 하위 호환, 점진 제거 |
| 로컬 SQLite | `silmari.db` | Git 미추적, 개인용 |

**운영 배포 시**
- [ ] `/dev` 라우트 비활성화 또는 빌드 제외
- [ ] `BOOTSTRAP_ADMIN_NO_PASSWORD=false`
- [ ] CORS 도메인 제한

---

## API ↔ 프론트 연결 매트릭스

| API | 프로덕션 UI | Dev UI | 미연결 |
|-----|-------------|--------|--------|
| `POST /cctv/analyze` | CCTVUpload | DevCctv | |
| `GET /detection-results` | SearchResults | DevResult | |
| `GET /detection-results/{id}` | — | DevResult | **프로덕션** |
| `GET /detection-results/history` | — | — | **양쪽** |
| `GET /detection-results/list` | — | DevResult | **프로덕션** |
| `POST /alerts/parse` | — | DevAlert | **프로덕션** |
| `GET /disaster-alerts` | Dashboard | DevDisaster | |
| `POST /auth/login` | — | DevAuth | **Login.jsx** |
| `GET /admin/users` | — | DevAdmin | **Admin views** |
| `GET /search-requests` | — | DevSearch | |
| `POST /chatbot/chat` | ChatbotPage | DevChatbot | |

---

## 삭제 전 공통 체크리스트 (복붙용)

```text
[ ] rg "파일명" .  → import 0건인가?
[ ] dev/ 테스트 전용이 아닌가?
[ ] README·주석에 "향후 사용" 계획이 없는가? (있으면 팀 합의)
[ ] 삭제 후 npm run build / pytest 통과하는가?
```

---

## 권장 작업 순서

```
1. ISSUE-001 (detect_missing_person → CCTV API)  ← 데모/발표에 가장 중요
2. ISSUE-003 (Login 연동)             ← RBAC 의미 있게 쓰려면
3. ISSUE-004 (검색 이력)
4. ISSUE-002 (인덱싱/검색 파이프라인) ← 수집-검색 분리 아키텍처 완성
5. ISSUE-101~107 (정리)              ← 기능 안정 후
6. ISSUE-006 (Admin)                 ← 운영 단계에서
```

---

## 관련 문서

- [프로젝트 README](../ReadMe.md)
- [지역 데이터 FAQ](../frontend/src/data/README.md)
