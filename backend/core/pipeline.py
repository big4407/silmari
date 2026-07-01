# core/pipeline.py
# ──────────────────────────────────────────────────────────────────────────
# 탐지 파이프라인 — 수집(인덱싱) / 검색 분리.
#
#   [인덱싱·전날] index_video_pipeline : 영상 → crop 임베딩 → Chroma + video_detail
#   [검색·당일]   search_pipeline       : MySQL로 지역·기간 필터(방식 B)
#                                         → Chroma threshold 검색 → 후보(0건 가능)
#
# 기존 run_detection_pipeline(업로드=즉시검색)은 호환을 위해 남겨둔다.
# ──────────────────────────────────────────────────────────────────────────
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.core.vision.matcher import index_video, search_persons
from backend.db.crud import MatchCandidate, search_embeddings
from backend.db.models import Video, VideoDetail


# ──────────────────────────────────────────────────────────────────────────
# 인덱싱 (전날) — 영상 1개를 처리해 Chroma 저장 + video_detail 기록
# ──────────────────────────────────────────────────────────────────────────
def index_video_pipeline(
    db: Session,
    video_path: str,
    cctv_serial_no: Optional[str] = None,
    region_code: Optional[str] = None,
    recorded_at: Optional[datetime] = None,
) -> dict:
    """영상을 인덱싱한다: video 행 생성 → crop 임베딩(Chroma) → video_detail 저장.

    반환: {"video_id", "indexed_count"}
    """
    # 1) video 행 먼저 생성 (id 확보)
    video = Video(
        cctv_serial_no=cctv_serial_no,
        file_path=video_path,
        region_code=region_code,
        recorded_at=recorded_at,
    )
    db.add(video)
    db.flush()   # video.id 확보

    # 2) 영상 → crop 임베딩 → Chroma 저장 (matcher가 처리)
    indexed = index_video(
        video_path=video_path,
        video_id=video.id,
        region_code=region_code,
    )

    # 3) video_detail 행들 저장 (Chroma id = embedding_id 로 매핑)
    for d in indexed:
        db.add(
            VideoDetail(
                video_id=video.id,
                video_timestamp=d.video_timestamp,
                crop_id=d.crop_id,
                position=d.position,
            )
        )

    # 4) video.embedding_id 에 대표 임베딩 키 기록(이 영상의 임베딩 묶음 식별용)
    #    개별 crop 의 embedding_id 는 video_detail 단위로 Chroma 에 있다.
    if indexed:
        video.embedding_id = f"video:{video.id}"

    db.commit()
    return {"video_id": video.id, "indexed_count": len(indexed)}


# ──────────────────────────────────────────────────────────────────────────
# 검색 (당일) — 지역·기간 필터(MySQL) → Chroma threshold 검색
# ──────────────────────────────────────────────────────────────────────────
def search_pipeline(
    db: Session,
    clothes_en: str,
    region_code: Optional[str] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    threshold: Optional[float] = None,
) -> list[MatchCandidate]:
    """인상착의(영문)로 검색. 방식 B: MySQL로 지역·기간을 먼저 거른 뒤,
    그 영상들의 임베딩 안에서만 Chroma 유사도 검색을 수행한다.

    기준을 넘는 후보가 없으면 빈 리스트("매칭 없음")를 반환한다.
    후보의 embedding_id 메타로 video / video_detail 상세를 채워 쓰면 된다.
    """
    if not clothes_en:
        return []

    has_filter = bool(region_code or start_time or end_time)

    # 1) MySQL: 지역·기간에 맞는 video.id 목록 (정형 필터는 MySQL 담당)
    video_ids = None
    if has_filter:
        stmt = select(Video.id)
        if region_code:
            stmt = stmt.where(Video.region_code == region_code)
        if start_time:
            stmt = stmt.where(Video.recorded_at >= start_time)
        if end_time:
            stmt = stmt.where(Video.recorded_at <= end_time)

        video_ids = [vid for (vid,) in db.execute(stmt).all()]
        if not video_ids:
            return []   # 조건에 맞는 영상 자체가 없음 → 매칭 없음

    # 2) Chroma: 그 video 들의 임베딩 안에서만 텍스트 유사도 threshold 검색
    #    (벡터 유사도는 Chroma 담당. video_id 메타 $in 으로 범위 제한)
    kwargs = {"region_code": region_code, "video_ids": video_ids}
    if threshold is not None:
        kwargs["threshold"] = threshold

    return search_persons(clothes_en, **kwargs)


# ──────────────────────────────────────────────────────────────────────────
# (레거시) 업로드=즉시검색 — 기존 cctv.py 호환용. 점진적으로 제거 예정.
# ──────────────────────────────────────────────────────────────────────────
def run_detection_pipeline(
    video_path: str, sms_text: str, reference_img_path: Optional[str] = None
) -> dict:
    """[DEPRECATED] 기존 단발 파이프라인. 새 구조(index/search)로 이전 중.
    호환을 위해 시그니처만 유지하며, 내부는 빈 결과를 돌려준다.
    실제 검색은 search_pipeline 을, 인덱싱은 index_video_pipeline 을 사용할 것.
    """
    return {
        "sms_info": {"raw_text": sms_text},
        "total_detections": 0,
        "face_recognition_used": reference_img_path is not None,
        "detections": [],
        "deprecated": True,
    }