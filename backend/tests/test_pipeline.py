# test_pipeline.py
# ──────────────────────────────────────────────────────────────────────────
# 인덱싱/검색 파이프라인 직접 테스트용 스크립트.
#
# 위치: backend/tests/test_pipeline.py
# 프로젝트 루트에서 실행:
#   python -m backend.tests.test_pipeline           # 로직 테스트 (모델 불필요, 바로 실행)
#   python -m backend.tests.test_pipeline --real    # 실제 테스트 (FashionCLIP·YOLO·영상 필요)
#
# 로직 테스트: 가짜 임베딩으로 Chroma 검색·기간 필터·0건 케이스만 확인.
# 실제 테스트: 진짜 영상을 인덱싱하고 인상착의로 검색 (무거움, 영상 파일 필요).
# ──────────────────────────────────────────────────────────────────────────
import sys
from datetime import datetime, timedelta


# ══════════════════════════════════════════════════════════════════════════
# 1) 로직 테스트 — 모델 없이 Chroma + 기간 필터 + 0건 확인
# ══════════════════════════════════════════════════════════════════════════
def test_logic():
    print("=" * 60)
    print(" 로직 테스트 (가짜 임베딩) — Chroma 검색 / 기간필터 / 0건")
    print("=" * 60)

    from backend.db import crud
    from backend.db.database import get_chromadb

    col = get_chromadb()

    # --- 준비: 가짜 임베딩 4개 저장 (실제론 인덱싱이 넣음) ---
    # video 1: 빨강 계열(1,0,0) 2건 / video 2: 파랑 계열(0,1,0) 1건 / video 3: 다른지역
    crud.index_embeddings(
        embedding_ids=["v1_c0", "v1_c1", "v2_c0", "v3_c0"],
        image_embeddings=[[1, 0, 0], [0.95, 0.05, 0], [0, 1, 0], [1, 0, 0]],
        metadatas=[
            {"video_id": 1, "region_code": "41110"},
            {"video_id": 1, "region_code": "41110"},
            {"video_id": 2, "region_code": "41110"},
            {"video_id": 3, "region_code": "41135"},
        ],
    )
    print(f"\n[준비] 임베딩 {crud.count_embeddings()}건 저장")

    # 쿼리 임베딩 (실제론 인상착의 텍스트 임베딩). 빨강(1,0,0)을 찾는다고 가정.
    red_query = [1.0, 0.0, 0.0]

    # --- 테스트 1: 전체에서 빨강 검색 (threshold 통과분만) ---
    hits = crud.search_embeddings(red_query, threshold=0.2)
    print(f"\n[1] 전체 빨강 검색 → {len(hits)}건")
    for h in hits:
        print(f"    {h.embedding_id}: sim={h.similarity} video={h.metadata.get('video_id')}")

    # --- 테스트 2: video_id [1] 로 제한 (방식 B — MySQL이 기간으로 골랐다고 가정) ---
    hits2 = crud.search_embeddings(red_query, threshold=0.2, video_ids=[1])
    print(f"\n[2] video_id=[1] 로 제한 → {len(hits2)}건 (v1_c0, v1_c1만, v3 제외)")
    for h in hits2:
        print(f"    {h.embedding_id}: video={h.metadata.get('video_id')}")

    # --- 테스트 3: 지역 필터 ---
    hits3 = crud.search_embeddings(red_query, threshold=0.2, region_code="41110")
    print(f"\n[3] region=41110 필터 → {len(hits3)}건 (41135의 v3 제외)")

    # --- 테스트 4: 매칭 없는 쿼리 → 0건 (핵심!) ---
    green_query = [0.0, 0.0, 1.0]  # 저장된 것과 무관한 방향
    none = crud.search_embeddings(green_query, threshold=0.2)
    print(f"\n[4] 무관한 쿼리 → {len(none)}건 (0이어야 정상 — top-k 아니라 threshold)")

    # --- 테스트 5: 빈 video_ids → 즉시 0건 (기간에 맞는 영상 없음) ---
    empty = crud.search_embeddings(red_query, threshold=0.2, video_ids=[])
    print(f"\n[5] video_ids=[] (기간 무매칭) → {len(empty)}건 (0이어야)")

    # --- 정리 ---
    crud.delete_embeddings(["v1_c0", "v1_c1", "v2_c0", "v3_c0"])
    print(f"\n[정리] 삭제 후 임베딩: {crud.count_embeddings()}건")

    print("\n✅ 로직 테스트 완료")


# ══════════════════════════════════════════════════════════════════════════
# 2) 실제 테스트 — FashionCLIP·YOLO·영상으로 인덱싱→검색
# ══════════════════════════════════════════════════════════════════════════
def test_real():
    print("=" * 60)
    print(" 실제 테스트 (FashionCLIP·YOLO·영상 필요)")
    print("=" * 60)

    from backend.db.database import SessionLocal, Base, engine
    from backend.core.pipeline import index_video_pipeline, search_pipeline

    # ── 여기 값을 네 환경에 맞게 수정 ──────────────────────────────
    VIDEO_PATH = "data/CCTV/output_video_521_1.mp4"          # 테스트할 영상 경로 (루트 기준 상대경로)
    REGION_CODE = "41110"                        # 지역코드
    RECORDED_AT = datetime(2026, 6, 28, 14, 0)   # 녹화 시각
    CLOTHES_EN = "a person wearing a red padded jacket and blue jeans"  # 영문 인상착의
    # ────────────────────────────────────────────────────────────

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # 1) 인덱싱 — 영상을 처리해 Chroma + video_detail 저장
        print(f"\n[인덱싱] {VIDEO_PATH} 처리 중... (모델 로딩으로 시간 걸림)")
        result = index_video_pipeline(
            db=db,
            video_path=VIDEO_PATH,
            cctv_serial_no="CCTV-TEST-001",
            region_code=REGION_CODE,
            recorded_at=RECORDED_AT,
        )
        print(f"[인덱싱 완료] video_id={result['video_id']}, "
              f"인덱싱된 인물 crop={result['indexed_count']}건")

        # 2) 검색 — 인상착의(영문)로 기간·지역 필터 후 유사도 검색
        print(f"\n[검색] '{CLOTHES_EN}'")
        print(f"       지역={REGION_CODE}, 기간={RECORDED_AT.date()} 전후")
        candidates = search_pipeline(
            db=db,
            clothes_en=CLOTHES_EN,
            region_code=REGION_CODE,
            start_time=RECORDED_AT - timedelta(hours=2),
            end_time=RECORDED_AT + timedelta(hours=2),
        )

        print(f"\n[검색 결과] 후보 {len(candidates)}건")
        if not candidates:
            print("    → 매칭 없음 (기준을 넘는 후보 없음)")
        for c in candidates[:10]:
            print(f"    {c.embedding_id}: 유사도={c.similarity} "
                  f"(video={c.metadata.get('video_id')}, ts={c.metadata.get('video_timestamp')}초)")

    finally:
        db.close()

    print("\n✅ 실제 테스트 완료")


if __name__ == "__main__":
    if "--real" in sys.argv:
        test_real()
    else:
        test_logic()
        print("\n💡 실제 영상·모델로 테스트하려면: python -m backend.tests.test_pipeline --real")