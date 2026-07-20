# SILMARI 독립형 통계 모듈

## 기존 코드 변경 범위

`backend/main.py`에 아래 두 줄만 추가합니다.

```python
from backend.stats.router import router as stats_router

app.include_router(stats_router)
```

## 기존 DB 매핑

기본 테이블명:

- video
- video_detail
- search
- analysis
- analysis_detail

실제 이름이 다르면 `backend/stats/config.py` 또는 `.env`의
`STATS_*` 값을 수정합니다.

예시:

```env
STATS_VIDEO_STATUS=index_status
STATS_VIDEO_COMPLETED_VALUE=completed
STATS_VIDEO_REGION=cctv_region
STATS_ANALYSIS_PROCESSING_MS=elapsed_ms
STATS_MATCH_THRESHOLD=0.75
STATS_SIMILARITY_MULTIPLIER=100
```

## 통계 전용 테이블

첫 API 호출 때 다음 테이블만 자동 생성됩니다.

- stats_case_event
- stats_export_log

기존 운영 테이블은 변경하지 않습니다.

## API

- GET /api/v1/admin/stats/cctv
- GET /api/v1/admin/stats/search
- GET /api/v1/admin/stats/demographic
- GET /api/v1/admin/stats/outcomes
- POST /api/v1/admin/stats/case-events
- GET /api/v1/admin/stats/case-events
- POST /api/v1/admin/stats/export
- GET /api/v1/admin/stats/exports
