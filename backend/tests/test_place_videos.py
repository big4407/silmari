"""
CCTV 파이프라인 통합 테스트(test_video_pipeline_integration.py)용 테스트 데이터를
한 번에 준비한다.

  1) create_cctv_directory.create_cctv_directories() 로
     {cctv_data_dir}/{region_code}/{YYYYMMDD}/{cctv_serial_no}/ 폴더 생성
  2) 방금 만든 폴더들을 순회하며 --source-dir(기본: settings.upload_dir,
     즉 data/uploads)의 샘플 영상을 폴더마다 0~--max-per-folder개(기본 3)
     무작위 개수로 복사

운영 코드가 아니라 테스트 픽스처 생성 스크립트라 tests/ 아래에 둔다. 파일명이
test_로 시작하지만 pytest가 자동 수집해서 실행할 test_* 함수는 없다 —
`python -m` 으로 수동 실행하는 스크립트다(test_video_pipeline_integration.py와
동일한 패턴).

사용 예:
  python -m backend.tests.test_place_videos --start-date 2026-07-01 --end-date 2026-07-07
  python -m backend.tests.test_place_videos --start-date 2026-07-01 --end-date 2026-07-01 \\
      --cctv-count 5 --max-per-folder 5 --seed 42
  python -m backend.tests.test_place_videos --start-date 2026-07-01 --end-date 2026-07-01 \\
      --source-dir /custom/videos/path
"""

from __future__ import annotations

import argparse
import random
import shutil
import uuid
from datetime import date
from pathlib import Path

from backend.core.config import settings
from backend.utils.create_cctv_directory import (
    _parse_date,
    create_cctv_directories,
)

_VIDEO_EXTENSIONS = {".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm"}


def find_leaf_folders(base_dir: Path) -> list[Path]:
    """{region_code}/{YYYYMMDD}/{cctv_serial_no} 3단계 깊이의 폴더만 찾는다."""
    if not base_dir.exists():
        return []
    return [p for p in base_dir.glob("*/*/*") if p.is_dir()]


def find_sample_videos(source_dir: Path) -> list[Path]:
    if not source_dir.exists():
        return []
    return [
        p
        for p in source_dir.rglob("*")
        if p.is_file() and p.suffix.lower() in _VIDEO_EXTENSIONS
    ]


def _has_existing_video(folder: Path) -> bool:
    return any(
        p.is_file() and p.suffix.lower() in _VIDEO_EXTENSIONS for p in folder.iterdir()
    )


def place_test_videos(
    source_dir: Path,
    base_dir: Path | None = None,
    max_per_folder: int = 3,
    seed: int | None = None,
) -> dict:
    """생성된 CCTV 폴더마다 0~max_per_folder개의 샘플 영상을 무작위로 복사한다.

    이미 영상이 있는 폴더는 건드리지 않고 건너뛴다(중복 배치 방지 — 실제 영상이
    이미 들어와 있는 폴더에 테스트용 영상을 더 얹지 않기 위해).

    반환값: {"folders": 대상 폴더 수, "placed": 실제로 복사한 파일 수,
             "empty_folders": 무작위 개수가 0이라 비워둔 폴더 수,
             "skipped_existing": 이미 영상이 있어서 건드리지 않은 폴더 수}
    """
    rng = random.Random(seed)
    base_dir = base_dir or Path(settings.cctv_data_dir)

    sample_videos = find_sample_videos(source_dir)
    if not sample_videos:
        print(f"[테스트 영상 배치] 샘플 영상이 없습니다: {source_dir}")
        return {"folders": 0, "placed": 0, "empty_folders": 0, "skipped_existing": 0}

    leaf_folders = find_leaf_folders(base_dir)
    if not leaf_folders:
        print(
            f"[테스트 영상 배치] 대상 폴더가 없습니다: {base_dir} "
            "— CCTV 폴더 생성이 먼저 되어야 합니다."
        )
        return {"folders": 0, "placed": 0, "empty_folders": 0, "skipped_existing": 0}

    placed = 0
    empty_folders = 0
    skipped_existing = 0
    for folder in leaf_folders:
        if _has_existing_video(folder):
            skipped_existing += 1
            continue

        count = rng.randint(0, max_per_folder)
        if count == 0:
            empty_folders += 1
            continue

        for _ in range(count):
            source = rng.choice(sample_videos)
            # 같은 폴더에 같은 원본이 여러 번 뽑혀도 안 겹치도록 고유 접미사를 붙인다.
            dest_name = f"{source.stem}_{uuid.uuid4().hex[:8]}{source.suffix}"
            shutil.copy2(source, folder / dest_name)
            placed += 1

    print(
        f"[테스트 영상 배치 완료] 대상 폴더 {len(leaf_folders)}개 중 "
        f"{skipped_existing}개는 이미 영상이 있어 건너뜀, {empty_folders}개는 "
        f"무작위로 빈 상태 유지 | 총 {placed}개 영상 배치 "
        f"(샘플 원본 {len(sample_videos)}개 중 무작위 선택, base: {base_dir})"
    )
    return {
        "folders": len(leaf_folders),
        "placed": placed,
        "empty_folders": empty_folders,
        "skipped_existing": skipped_existing,
    }


def setup_test_video_data(
    start_date: date,
    end_date: date,
    source_dir: Path,
    cctv_count: int = 3,
    max_per_folder: int = 3,
    region_codes: list[str] | None = None,
    seed: int | None = None,
) -> dict:
    """CCTV 폴더 생성 + 샘플 영상 배치를 한 번에 실행한다."""
    base_dir = Path(settings.cctv_data_dir)

    create_cctv_directories(
        start_date=start_date,
        end_date=end_date,
        cctv_count=cctv_count,
        region_codes=region_codes,
    )
    return place_test_videos(
        source_dir=source_dir,
        base_dir=base_dir,
        max_per_folder=max_per_folder,
        seed=seed,
    )


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="CCTV 폴더 생성 + 샘플 영상 무작위 배치를 한 번에 실행한다."
    )
    parser.add_argument(
        "--start-date", required=True, type=_parse_date, help="YYYY-MM-DD"
    )
    parser.add_argument(
        "--end-date", required=True, type=_parse_date, help="YYYY-MM-DD"
    )
    parser.add_argument(
        "--cctv-count",
        type=int,
        default=3,
        help="지역마다 생성할 CCTV 폴더 개수 (기본 3)",
    )
    parser.add_argument(
        "--region-code",
        action="append",
        dest="region_codes",
        help="특정 region_code만 대상으로 하려면 반복 지정 (안 주면 Region 테이블의 "
        "최하위 지역 전체)",
    )
    parser.add_argument(
        "--source-dir",
        type=Path,
        default=None,
        help="샘플 영상들이 있는 폴더 (기본: settings.upload_dir, 즉 data/uploads)",
    )
    parser.add_argument(
        "--max-per-folder",
        type=int,
        default=3,
        help="폴더 하나당 최대 배치 개수 (0~이 값 사이에서 무작위, 기본 3)",
    )
    parser.add_argument(
        "--seed", type=int, default=None, help="재현 가능한 결과가 필요하면 지정"
    )
    return parser


if __name__ == "__main__":
    args = _build_arg_parser().parse_args()
    if args.end_date < args.start_date:
        raise SystemExit("--end-date는 --start-date 이후(또는 같은 날)여야 합니다.")

    setup_test_video_data(
        start_date=args.start_date,
        end_date=args.end_date,
        source_dir=args.source_dir or Path(settings.upload_dir),
        cctv_count=args.cctv_count,
        max_per_folder=args.max_per_folder,
        region_codes=args.region_codes,
        seed=args.seed,
    )
