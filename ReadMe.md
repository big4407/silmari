# 실마리 (Silmari)

실종자 인상착의 파싱 + CCTV 영상 매칭 시스템

## 프로젝트 구조

```
silmari/
├── backend/          # FastAPI + LangChain + Vision
├── frontend/         # React + Leaflet 지도
├── models/yolo/      # YOLO 가중치
├── data/             # CCTV 영상, 탐지 결과
└── docker-compose.yml
```

## 실행 방법

### 백엔드
```bash
cd backend

# 방법 1: 기존 환경 복사됨 (.venv 있으면)
.venv\Scripts\activate        # Windows
uvicorn main:app --reload

# 방법 2: 새로 설치
pip install -r requirements.txt
uvicorn main:app --reload
```

`.env` 파일은 `missing-person-finder/backend/.env`에서 수동 복사하세요.
YOLO 모델: `models/yolo/yolov8n.pt` (이미 복사됨)

### 프론트엔드
```bash
cd frontend
npm install
npm run dev
```

- 프론트: http://localhost:5173
- API: http://localhost:8000

## API 엔드포인트

| 경로 | 설명 |
|------|------|
| `POST /api/alert/parse` | 안내문자 인상착의 파싱 |
| `POST /api/cctv/analyze` | CCTV 영상 분석 |
| `GET /api/result/list` | 실종자 목록 조회 |

## 페이지

- `/` — 대시보드 (지도 + 인상착의 카드)
- `/alert` — 안내문자 입력
- `/cctv` — CCTV 영상 업로드
- `/result` — 탐지 결과
