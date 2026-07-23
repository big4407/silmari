"""
테스트 환경을 한 번에 세팅한다.

  1) data/uploads(settings.upload_dir)의 원본 샘플 영상을 소스로 사용
  2) test_Message.insert_test_messages() 로 테스트용 실종 안내문자 삽입
  3) test_place_videos.setup_test_video_data_from_messages() 로 그 문자들의
     (지역, 날짜) 기준 CCTV 폴더 생성 + 영상 배치
  4) VideoService.process_videos() 로 실제 인물 탐지·임베딩까지 완료
     (여기서 실제 검색이 가능한 상태가 됨 — 폴더에 영상만 있고 인덱싱 안 하면
     Chroma에 아무것도 없어서 검색해도 매칭이 안 됨)

[왜 오래 걸리는지 / 시간 제한 방법]
가장 무거운 단계는 4번(YOLO 인물 탐지 + FashionCLIP 임베딩, 영상 1개당 수 초~
수십 초)이지, 폴더 생성이나 파일 복사가 아니다. 그래서 이 스크립트는 두 가지로
시간을 제한한다:
  - CCTV 폴더당 영상을 정확히 1개만 배치(cctv_count=1, max_per_folder=1) —
    "몇 개가 들어갈지 무작위"였던 기존 동작 대신 예측 가능한 개수로 고정.
  - 실제 인덱싱(process_videos)에 넘기는 영상 개수 자체를 --max-videos(기본 5)로
    상한 — 폴더에는 더 배치돼 있어도, 무거운 4번 단계는 그중 앞에서부터
    max_videos개까지만 돌린다. 나머지는 폴더에 남아있으니 나중에 필요하면
    수동으로 더 인덱싱하면 된다.

운영 코드가 아니라 테스트 환경 준비용 스크립트라 tests/ 아래에 둔다. pytest가
자동 수집해서 실행할 test_* 함수는 없다 — `python -m` 으로 수동 실행한다.

사용 예:
  python -m backend.tests.test_setup_environment
  python -m backend.tests.test_setup_environment --message-count 5 --max-videos 3
  python -m backend.tests.test_setup_environment --region "대전광역시 동구 가양동" --clear-existing-messages
  python -m backend.tests.test_setup_environment --clear-existing-videos
      # video 관련 데이터 + Chroma 임베딩을 싹 지우고 재세팅(운영 데이터 없는
      # 로컬 개발 DB에서만 사용). 안 지우고 재실행하면 video.id가 나중에
      # 재사용될 때 Chroma에 남은 옛 임베딩이 새 영상과 잘못 매칭될 수 있다.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from backend.core.config import settings
from backend.db.database import SessionLocal, delete_video_embeddings
from backend.db.models import AnalysisDetail, Video
from backend.repositories.region_repository import RegionRepository
from backend.services.region_admin_service import RegionAdminService
from backend.services.video_service import VideoService
from backend.tests.test_Message import insert_test_messages
from backend.tests.test_place_videos import setup_test_video_data_from_messages


def _select_videos_balanced(placed_paths: list[str], max_videos: int) -> list[str]:
    """경로 안의 region_code(시군구 prefix)별로 라운드로빈해 인덱싱 대상을 고른다."""
    from collections import defaultdict, deque

    if max_videos <= 0 or not placed_paths:
        return []

    groups: dict[str, deque[str]] = defaultdict(deque)
    for path in placed_paths:
        parts = Path(path).parts
        # .../CCTV/{region_code}/{YYYYMMDD}/{cctv}/file.mp4
        region_code = next(
            (p for p in parts if p.isdigit() and len(p) >= 5),
            "unknown",
        )
        groups[region_code[:5]].append(path)

    selected: list[str] = []
    while len(selected) < max_videos and groups:
        empty_keys: list[str] = []
        for key in list(groups.keys()):
            if len(selected) >= max_videos:
                break
            bucket = groups[key]
            if bucket:
                selected.append(bucket.popleft())
            if not bucket:
                empty_keys.append(key)
        for key in empty_keys:
            del groups[key]
    return selected


def _ensure_region_data(db, csv_path: Path | None = None) -> None:
    """region 테이블이 비어있으면 administrative_dong.csv로 채운다.

    지역명 → region_code 해석(챗봇 validate_region_node, CCTV 폴더 배치의
    region_code 기준 등) 전체가 region 테이블을 전제로 한다. 빈 DB에서
    이 스크립트를 그대로 돌리면 region이 비어있어 지역 해석이 전부 실패해
    문자 삽입은 되어도 영상 배치·검색이 제대로 안 됐다.

    RegionAdminService.import_administrative_dong_csv()를 그대로 재사용한다
    (admin 콘솔의 CSV 업로드 적재 로직과 동일 — 새로 만들 이유가 없다).
    이미 데이터가 있으면 손대지 않는다 — 파괴적 동작이 아니라서 opt-in
    플래그 없이 항상 실행한다(비어있을 때만 실제로 적재가 일어남).
    """
    existing = RegionRepository(db).count()
    if existing > 0:
        print(f"[지역 데이터] region 테이블에 이미 {existing}건 있어 건너뜀")
        return

    path = csv_path or settings.administrative_dong_csv
    print(f"[지역 데이터] region 테이블이 비어있어 {path} 로 채웁니다")

    result = RegionAdminService(db).import_administrative_dong_csv(path)
    if result.errors:
        print(f"[지역 데이터] 적재 실패: {'; '.join(result.errors)}")
        return

    print(
        f"[지역 데이터] 시도 {result.sido_count}, 시군구 {result.sigungu_count}, "
        f"행정동 {result.admin_dong_count}, 법정동 매핑 {result.legal_dong_count}건 적재 완료"
    )


def _clear_existing_video_data(db) -> dict:
    """video/video_detail/analysis_detail/Chroma 임베딩을 모두 지운다.

    test_Message처럼 sn에 T 접두어를 붙여 테스트 데이터만 안전하게 골라
    지우는 방식이 video에는 없다 — 영상은 실제 CCTV 데이터와 같은 폴더
    구조(cctv_data_dir/{region_code}/{YYYYMMDD}/{cctv})에 배치되고, video
    행에 테스트 전용 마커가 없기 때문이다. 그래서 이 함수는 video 테이블
    전체를 지운다 — 운영 데이터가 섞인 환경에서는 절대 쓰지 말 것
    (--clear-existing-videos 플래그로만 opt-in, 기본은 항상 꺼짐).

    반드시 video 행을 지우기 전에 Chroma 임베딩부터 지운다 — 안 그러면
    video.id(AUTO_INCREMENT)가 재인덱싱 때 재사용될 경우, Chroma에 남은
    옛 임베딩이 새로 들어온 영상과 잘못 매칭되어 "엉뚱한 영상이 재생되는"
    버그로 이어진다(delete_video_embeddings 문서 참고).

    analysis_detail.video_id는 FK인데 Video → AnalysisDetail로의 ORM
    cascade가 없어서(Analysis → AnalysisDetail cascade만 있음), video를
    지우기 전에 그 video를 참조하는 analysis_detail 행을 먼저 지워야
    FK 제약 위반이 안 난다.
    """
    videos = db.query(Video).all()
    video_ids = [v.id for v in videos]

    if not video_ids:
        return {"videos_deleted": 0, "analysis_details_deleted": 0}

    deleted_details = (
        db.query(AnalysisDetail)
        .filter(AnalysisDetail.video_id.in_(video_ids))
        .delete(synchronize_session=False)
    )

    for video_id in video_ids:
        try:
            delete_video_embeddings(video_id)
        except Exception as exc:  # noqa: BLE001
            print(
                f"[테스트 환경 초기화] Chroma 임베딩 삭제 실패 "
                f"video_id={video_id}: {exc}"
            )

    for video in videos:
        db.delete(video)  # video_detail은 cascade="all, delete-orphan"으로 같이 지워짐

    db.commit()

    print(
        f"[테스트 환경 초기화] video {len(video_ids)}건, "
        f"analysis_detail {deleted_details}건 삭제 + Chroma 임베딩 정리 완료"
    )

    return {
        "videos_deleted": len(video_ids),
        "analysis_details_deleted": deleted_details,
    }


def setup_test_environment(
    message_count: int = 10,
    regions: list[str] | None = None,
    clear_existing_messages: bool = False,
    clear_existing_videos: bool = False,
    max_videos: int = 5,
    max_pairs: int = 20,
    seed: int | None = None,
    administrative_dong_csv: Path | None = None,
) -> dict:
    source_dir = Path(settings.upload_dir)

    db = SessionLocal()
    try:
        _ensure_region_data(db, administrative_dong_csv)
    finally:
        db.close()

    if clear_existing_videos:
        print("[0/3] 기존 영상 데이터 초기화 (video/video_detail/analysis_detail/Chroma)")
        db = SessionLocal()
        try:
            _clear_existing_video_data(db)
        finally:
            db.close()

    print("[1/3] 테스트용 실종 안내문자 삽입 (test_Message)")
    message_result = insert_test_messages(
        count=message_count,
        regions=regions,
        clear_existing=clear_existing_messages,
    )

    print("\n[2/3] Message 기반 CCTV 폴더 생성 + 영상 배치 (test_place_videos)")
    # 폴더당 정확히 1개만 배치 — 인덱싱할 영상 개수를 처음부터 예측 가능하게 한다.
    # min_per_folder=1을 반드시 같이 줘야 한다 — max_per_folder=1만 주면
    # _distribute_videos가 매 폴더마다 0~1 중 무작위로 뽑아서(50% 확률로 0),
    # 어떤 문자는 배치된 영상이 하나도 없어 그 문자로 검색해도 결과가 안
    # 나오는 문제가 있었다. min=max=1로 고정해서 "정확히 1개"를 실제로 보장한다.
    # max_pairs로 (지역,날짜) 조합 자체도 제한 — 지역명이 넓게 매칭되면(예: 짧은
    # 지역명이 여러 동에 걸리는 경우) 폴더 생성 대상이 메시지 개수보다 훨씬
    # 많아질 수 있어서, 폴더 생성 단계 자체도 시간이 오래 걸릴 수 있다.
    placement_result = setup_test_video_data_from_messages(
        source_dir=source_dir,
        cctv_count=1,
        max_per_folder=1,
        min_per_folder=1,
        seed=seed,
        max_pairs=max_pairs if max_pairs > 0 else None,
    )

    placed_paths = placement_result.get("placed_paths", [])
    # 앞에서부터 자르면 같은 지역(예: 서울)만 인덱싱되어, 다른 지역 문자는
    # 검색해도 후보 영상이 0건이 된다. region_code 기준으로 골고루 고른다.
    videos_to_index = _select_videos_balanced(placed_paths, max_videos)
    skipped_for_time = len(placed_paths) - len(videos_to_index)

    print(
        f"\n[3/3] 영상 분석(YOLO+FashionCLIP) 실행 — 배치된 {len(placed_paths)}개 중 "
        f"{len(videos_to_index)}개만 인덱싱(--max-videos={max_videos})"
        + (f", {skipped_for_time}개는 시간 제한으로 건너뜀" if skipped_for_time > 0 else "")
    )

    if not videos_to_index:
        print("[영상 분석] 인덱싱할 영상이 없습니다 — 2단계에서 배치된 영상이 없는지 확인하세요.")
        analysis_result = {"processed": 0, "skipped": 0, "failed": 0}
    else:
        db = SessionLocal()
        try:
            analysis_result = VideoService(db).process_videos(videos_to_index)
        finally:
            db.close()

    print(
        f"\n[테스트 환경 세팅 완료] 안내문자 {message_result['inserted']}건 삽입, "
        f"영상 {len(placed_paths)}개 배치, 그중 {analysis_result['processed']}개 "
        f"인덱싱 성공({analysis_result['skipped']}개 중복, "
        f"{analysis_result['failed']}개 실패)"
    )

    return {
        "message_result": message_result,
        "placement_result": placement_result,
        "analysis_result": analysis_result,
        "videos_skipped_for_time_limit": skipped_for_time,
    }


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="테스트 환경을 한 번에 세팅한다(안내문자 → CCTV 폴더/영상 배치 → 영상 분석)."
    )
    parser.add_argument(
        "--message-count", type=int, default=10, help="넣을 테스트 안내문자 건수 (기본 10)"
    )
    parser.add_argument(
        "--region",
        action="append",
        dest="regions",
        help="테스트 안내문자의 수신지역명(반복 지정 가능). 안 주면 test_Message의 "
        "기본 예시 지역을 씀 — 실제 Region 테이블과 맞는 지역명 권장",
    )
    parser.add_argument(
        "--clear-existing-messages",
        action="store_true",
        help="넣기 전에 SN이 T로 시작하는 기존 테스트 안내문자를 먼저 삭제",
    )
    parser.add_argument(
        "--clear-existing-videos",
        action="store_true",
        help="넣기 전에 video/video_detail/analysis_detail과 그 Chroma 임베딩을 "
        "모두 삭제한다. video엔 테스트/운영 구분 마커가 없어 테이블 전체를 "
        "지운다 — 운영 데이터가 섞인 환경에서는 쓰지 말 것. 기본은 꺼짐",
    )
    parser.add_argument(
        "--max-videos",
        type=int,
        default=5,
        help="실제 인덱싱(YOLO+FashionCLIP)까지 돌릴 영상 개수 상한 (기본 5) — "
        "가장 오래 걸리는 단계라 여기를 제한해야 전체 세팅 시간이 예측 가능함",
    )
    parser.add_argument(
        "--max-pairs",
        type=int,
        default=20,
        help="폴더 생성 단계에서 다룰 (지역,날짜) 조합 개수 상한 (기본 20) — "
        "지역명이 넓게 매칭되면 메시지 몇 건만 넣어도 폴더 생성 대상이 훨씬 "
        "많아질 수 있어 제한한다. 0 이하를 주면 상한 없음",
    )
    parser.add_argument(
        "--seed", type=int, default=None, help="영상 배치 재현 가능한 결과가 필요하면 지정"
    )
    parser.add_argument(
        "--administrative-dong-csv",
        type=Path,
        default=None,
        help="region 테이블이 비어있을 때 채울 administrative_dong.csv 경로 "
        "(기본: settings.administrative_dong_csv, 보통 data/raw/administrative_dong.csv)",
    )
    return parser


if __name__ == "__main__":
    args = _build_arg_parser().parse_args()
    setup_test_environment(
        message_count=args.message_count,
        regions=args.regions,
        clear_existing_messages=args.clear_existing_messages,
        clear_existing_videos=args.clear_existing_videos,
        max_videos=args.max_videos,
        max_pairs=args.max_pairs,
        seed=args.seed,
        administrative_dong_csv=args.administrative_dong_csv,
    )