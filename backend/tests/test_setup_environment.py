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
"""
from __future__ import annotations

import argparse
from pathlib import Path

from backend.core.config import settings
from backend.db.database import SessionLocal
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


def setup_test_environment(
    message_count: int = 10,
    regions: list[str] | None = None,
    clear_existing_messages: bool = False,
    max_videos: int = 5,
    max_pairs: int = 20,
    seed: int | None = None,
) -> dict:
    source_dir = Path(settings.upload_dir)

    print("[1/3] 테스트용 실종 안내문자 삽입 (test_Message)")
    message_result = insert_test_messages(
        count=message_count,
        regions=regions,
        clear_existing=clear_existing_messages,
    )

    print("\n[2/3] Message 기반 CCTV 폴더 생성 + 영상 배치 (test_place_videos)")
    # 폴더당 정확히 1개만 배치 — 인덱싱할 영상 개수를 처음부터 예측 가능하게 한다.
    # max_pairs로 (지역,날짜) 조합 자체도 제한 — 지역명이 넓게 매칭되면(예: 짧은
    # 지역명이 여러 동에 걸리는 경우) 폴더 생성 대상이 메시지 개수보다 훨씬
    # 많아질 수 있어서, 폴더 생성 단계 자체도 시간이 오래 걸릴 수 있다.
    placement_result = setup_test_video_data_from_messages(
        source_dir=source_dir,
        cctv_count=1,
        max_per_folder=1,
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
    return parser


if __name__ == "__main__":
    args = _build_arg_parser().parse_args()
    setup_test_environment(
        message_count=args.message_count,
        regions=args.regions,
        clear_existing_messages=args.clear_existing_messages,
        max_videos=args.max_videos,
        max_pairs=args.max_pairs,
        seed=args.seed,
    )