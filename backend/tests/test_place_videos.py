"""
CCTV 파이프라인 통합 테스트(test_video_pipeline_integration.py)용 테스트 데이터를
한 번에 준비한다.

두 가지 모드가 있다:

1) 범위 지정 모드 (기존) — --start-date/--end-date로 넓은 기간·전체 지역에
   무작위로 영상을 채운다.
2) Message 기반 모드 (신규, --from-messages) — Message 테이블 중 SN이 "T"로
   시작하는(test_Message.py로 넣은 테스트) 문자의 지역·생성일시 기준으로,
   실제 검색이 실행될 법한 (지역, 날짜) 조합에만 정확히 영상을 채운다. 실제
   API로 수집된 문자는 안 건드리고 안 본다(전체 스캔 안 해서 실데이터가 많아도
   느려지지 않음). 무작위 범위보다 훨씬 적은 폴더만 만들지만, 실제 파이프라인
   테스트(문자 선택 → 검색 → 매칭 확인)가 "매칭 대상이 아예 없어서 실패"하는
   일 없이 실제로 매칭까지 확인된다.

운영 코드가 아니라 테스트 픽스처 생성 스크립트라 tests/ 아래에 둔다. 파일명이
test_로 시작하지만 pytest가 자동 수집해서 실행할 test_* 함수는 없다 —
`python -m` 으로 수동 실행하는 스크립트다(test_video_pipeline_integration.py와
동일한 패턴).

사용 예:
  # 범위 지정 모드
  python -m backend.tests.test_place_videos --start-date 2026-07-01 --end-date 2026-07-07

  # Message 기반 모드 — Message 테이블에 있는 지역·날짜에만 정확히 채움
  python -m backend.tests.test_place_videos --from-messages
  python -m backend.tests.test_place_videos --from-messages --cctv-count 5 --seed 42
"""

from __future__ import annotations

import argparse
import random
import shutil
import uuid
from datetime import date
from pathlib import Path

from backend.core.config import settings
from backend.db.database import SessionLocal
from backend.db.models import Message
from backend.repositories.region_repository import RegionRepository
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


def _limit_pairs_balanced(
    pairs: list[tuple[str, date]], max_pairs: int
) -> list[tuple[str, date]]:
    """(region_code, date) 목록을 시군구 prefix별로 라운드로빈해 max_pairs개만 남긴다."""
    from collections import defaultdict, deque

    groups: dict[str, deque[tuple[str, date]]] = defaultdict(deque)
    for pair in pairs:
        groups[pair[0][:5]].append(pair)

    selected: list[tuple[str, date]] = []
    while len(selected) < max_pairs and groups:
        empty_keys: list[str] = []
        for key in list(groups.keys()):
            if len(selected) >= max_pairs:
                break
            bucket = groups[key]
            if bucket:
                selected.append(bucket.popleft())
            if not bucket:
                empty_keys.append(key)
        for key in empty_keys:
            del groups[key]
    return selected


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


def _distribute_videos(
    folders: list[Path],
    sample_videos: list[Path],
    max_per_folder: int,
    rng: random.Random,
) -> dict:
    """folders 각각에 0~max_per_folder개의 샘플 영상을 무작위로 복사한다.

    이미 영상이 있는 폴더는 건드리지 않고 건너뛴다(중복 배치 방지). 같은 원본
    영상이 서로 다른 폴더에 겹쳐 들어가지 않는다 — 전체 배치 과정에서 한 번
    쓰인 영상은 다시 안 쓴다(테스트할 때 같은 영상이 여러 곳에 나오면
    헷갈리기 때문). 원본 개수보다 필요한 슬롯이 많으면 원본이 소진된 뒤로는
    그냥 빈 채로 남긴다.
    """
    placed = 0
    empty_folders = 0
    skipped_existing = 0
    exhausted_folders = 0
    placed_paths: list[str] = []

    # 전체 배치 과정에서 공유하는 "아직 안 쓴 원본" 풀 — 여기서 뽑아 쓰면 그
    # 원본은 다시 안 뽑히므로, 서로 다른 폴더끼리 같은 영상이 안 겹친다.
    available = list(sample_videos)
    rng.shuffle(available)

    for folder in folders:
        if _has_existing_video(folder):
            skipped_existing += 1
            continue

        count = rng.randint(0, max_per_folder)
        if count == 0:
            empty_folders += 1
            continue

        placed_here = 0
        for _ in range(count):
            if not available:
                break
            source = available.pop()
            dest_name = f"{source.stem}_{uuid.uuid4().hex[:8]}{source.suffix}"
            dest_path = folder / dest_name
            shutil.copy2(source, dest_path)
            placed += 1
            placed_here += 1
            placed_paths.append(str(dest_path))

        if placed_here == 0 and count > 0:
            # 배치하려 했지만 그 시점에 이미 원본이 다 소진된 경우.
            exhausted_folders += 1

    return {
        "folders": len(folders),
        "placed": placed,
        "empty_folders": empty_folders,
        "skipped_existing": skipped_existing,
        "exhausted_folders": exhausted_folders,
        "placed_paths": placed_paths,
    }


def place_test_videos(
    source_dir: Path,
    base_dir: Path | None = None,
    max_per_folder: int = 3,
    seed: int | None = None,
) -> dict:
    """base_dir 밑의 모든 CCTV 리프 폴더에 샘플 영상을 무작위로 배치한다(범위 지정 모드용).

    반환값: {"folders", "placed", "empty_folders", "skipped_existing",
             "exhausted_folders", "placed_paths"}
    """
    rng = random.Random(seed)
    base_dir = base_dir or Path(settings.cctv_data_dir)
    empty_result = {
        "folders": 0,
        "placed": 0,
        "empty_folders": 0,
        "skipped_existing": 0,
        "exhausted_folders": 0,
        "placed_paths": [],
    }

    sample_videos = find_sample_videos(source_dir)
    if not sample_videos:
        print(f"[테스트 영상 배치] 샘플 영상이 없습니다: {source_dir}")
        return empty_result

    leaf_folders = find_leaf_folders(base_dir)
    if not leaf_folders:
        print(
            f"[테스트 영상 배치] 대상 폴더가 없습니다: {base_dir} "
            "— CCTV 폴더 생성이 먼저 되어야 합니다."
        )
        return empty_result

    result = _distribute_videos(leaf_folders, sample_videos, max_per_folder, rng)
    print(
        f"[테스트 영상 배치 완료] 대상 폴더 {result['folders']}개 중 "
        f"{result['skipped_existing']}개는 이미 영상이 있어 건너뜀, "
        f"{result['empty_folders']}개는 무작위로 빈 상태 유지"
        + (
            f", {result['exhausted_folders']}개는 원본 소진으로 못 채움"
            if result["exhausted_folders"]
            else ""
        )
        + f" | 총 {result['placed']}개 영상 배치 "
        f"(샘플 원본 {len(sample_videos)}개, 폴더당 서로 다른 영상만 사용, base: {base_dir})"
    )
    return result


def resolve_message_region_date_pairs(db) -> list[tuple[str, date]]:
    """Message 테이블의 각 문자를 (region_code, 날짜) 조합으로 변환한다.

    SN이 "T"로 시작하는(=test_Message.py로 넣은 테스트) 문자만 본다 — 실제 API로
    수집된 문자가 쌓이면 그 전체를 스캔하는 게 느려질뿐더러, 테스트 환경 세팅에
    실데이터가 섞여 들어가는 것도 맞지 않다.

    rcptn_rgn_nm(자유 텍스트 지역명)은 RegionRepository.find_codes_by_keyword로
    region_code 후보를 찾는다 — analysis_service.py의 지역 매칭과 동일한 로직을
    재사용해서, "실제 검색 때 걸릴 지역"과 "테스트 영상이 들어가는 지역"이
    어긋나지 않게 한다. 매칭된 코드 중 최하위(읍/면/동) 지역만 남기고
    시/도·시/군/구 같은 상위 계층은 버린다(CCTV는 항상 최하위 지역에만 있음).
    지역명이 하나도 안 걸리거나(리프가 아닌 것만 걸린 경우 포함) crt_dt가 없는
    문자는 건너뛴다. 여러 문자가 같은 (region_code, 날짜)로 겹치면 한 번만
    남긴다.
    """
    region_repository = RegionRepository(db)
    leaf_codes = set(region_repository.get_leaf_codes())
    pairs: set[tuple[str, date]] = set()
    skipped_no_region = 0

    messages = db.query(Message).filter(Message.sn.like("T%")).all()
    for message in messages:
        if not message.rcptn_rgn_nm or not message.crt_dt:
            continue

        matched_codes = region_repository.find_codes_by_keyword(
            message.rcptn_rgn_nm.strip()
        )
        # find_codes_by_keyword는 시/도·시/군/구 같은 상위 계층도 매칭될 수 있다
        # (예: 수신지역명이 "전북특별자치도"처럼 광역 단위면 2자리 시/도 코드가
        # 그대로 걸림). CCTV는 항상 최하위(읍/면/동)에만 있으므로 리프가 아닌
        # 코드는 여기서 걸러낸다 — 안 그러면 실제로 있을 수 없는 폴더
        # (예: data/CCTV/36/...)가 생긴다.
        region_codes = [code for code in matched_codes if code in leaf_codes]
        if not region_codes:
            skipped_no_region += 1
            continue

        target_date = message.crt_dt.date()
        for region_code in region_codes:
            pairs.add((region_code, target_date))

    if skipped_no_region:
        print(
            f"[Message 기반] 지역명이 Region 테이블과 안 걸려서 건너뛴 문자 "
            f"{skipped_no_region}건"
        )

    return sorted(pairs)


def setup_test_video_data_from_messages(
    source_dir: Path,
    cctv_count: int = 3,
    max_per_folder: int = 3,
    seed: int | None = None,
    max_pairs: int | None = 20,
) -> dict:
    """Message 테이블에 있는 실제 문자(지역·생성일시) 기준으로만 CCTV 폴더를
    만들고 샘플 영상을 배치한다.

    범위 지정 모드처럼 넓게 무작위로 뿌리지 않고, 실제 검색 조건과 정확히
    맞아떨어지는 (지역, 날짜)에만 데이터를 넣는다 — 파이프라인을 끝까지
    돌려봤을 때 "애초에 매칭 대상이 없어서" 실패하는 걸 방지한다.

    max_pairs: (지역, 날짜) 조합 개수 상한(기본 20). find_codes_by_keyword가
    지역명을 LIKE '%키워드%'로 넓게 매칭해서, 문자의 수신지역명이 짧거나
    흔한 이름이면 그 안의 동(洞)이 수십 개씩 걸릴 수 있다 — 메시지 몇 건만
    넣었는데도 폴더 생성 대상이 예상보다 훨씬 많아지는 걸 막는 안전장치.
    None으로 주면 상한 없이 전부 처리한다.
    """
    with SessionLocal() as db:
        pairs = resolve_message_region_date_pairs(db)

    if not pairs:
        print(
            "[Message 기반 테스트 데이터] 대상이 없습니다 — Message 테이블이 "
            "비어있거나, rcptn_rgn_nm이 Region 테이블과 안 걸립니다."
        )
        return {
            "message_pairs": 0,
            "folders": 0,
            "placed": 0,
            "exhausted_folders": 0,
            "placed_paths": [],
        }

    total_pairs_found = len(pairs)
    if max_pairs is not None and total_pairs_found > max_pairs:
        # sorted(pairs)가 region_code 오름차순이라, 그냥 앞에서 자르면 지역코드가
        # 작은 지역들만 남고 나머지는 통째로 버려진다("지역 순서대로만 폴더가
        # 생기는" 것처럼 보이는 원인). 무작위로 골라서 이 편향을 없앤다.
        rng_pairs = random.Random(seed)
        pairs = rng_pairs.sample(pairs, max_pairs)
        print(
            f"[Message 기반] 지역명 매칭으로 (지역,날짜) 조합이 {total_pairs_found}개나 "
            f"나와서 --max-pairs={max_pairs}개로 무작위 축소합니다 (수신지역명이 넓게 "
            "매칭됐을 수 있음 — 필요하면 --max-pairs로 조정)."
        )

    sample_videos = find_sample_videos(source_dir)
    if not sample_videos:
        print(f"[테스트 영상 배치] 샘플 영상이 없습니다: {source_dir}")
        return {
            "message_pairs": len(pairs),
            "folders": 0,
            "placed": 0,
            "exhausted_folders": 0,
            "placed_paths": [],
        }

    base_dir = Path(settings.cctv_data_dir)
    target_folders: list[Path] = []

    for region_code, target_date in pairs:
        create_cctv_directories(
            start_date=target_date,
            end_date=target_date,
            cctv_count=cctv_count,
            region_codes=[region_code],
        )
        date_dir = base_dir / region_code / target_date.strftime("%Y%m%d")
        target_folders.extend(p for p in date_dir.glob("*") if p.is_dir())

    rng = random.Random(seed)
    result = _distribute_videos(target_folders, sample_videos, max_per_folder, rng)
    result["message_pairs"] = len(pairs)

    print(
        f"[Message 기반 완료] 문자에서 뽑은 (지역,날짜) 조합 {len(pairs)}개 "
        f"(전체 매칭 {total_pairs_found}개 중) → "
        f"대상 폴더 {result['folders']}개 중 {result['skipped_existing']}개는 "
        f"이미 영상 있어 건너뜀, {result['empty_folders']}개는 무작위로 빈 상태 "
        f"유지"
        + (
            f", {result['exhausted_folders']}개는 원본 소진으로 못 채움"
            if result["exhausted_folders"]
            else ""
        )
        + f" | 총 {result['placed']}개 영상 배치(폴더당 서로 다른 영상만 사용)"
    )
    return result


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
        "--from-messages",
        action="store_true",
        help="Message 테이블의 실제 지역·생성일시 기준으로만 배치(범위 지정 옵션 무시)",
    )
    parser.add_argument(
        "--start-date", type=_parse_date, help="YYYY-MM-DD (--from-messages 아닐 때 필수)"
    )
    parser.add_argument(
        "--end-date", type=_parse_date, help="YYYY-MM-DD (--from-messages 아닐 때 필수)"
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
        help="특정 region_code만 대상으로 하려면 반복 지정 (범위 지정 모드 전용, "
        "안 주면 Region 테이블의 최하위 지역 전체)",
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
        "--max-pairs",
        type=int,
        default=20,
        help="--from-messages 전용 — (지역,날짜) 조합 개수 상한(기본 20). "
        "지역명이 넓게 매칭되면 폴더 생성 대상이 예상보다 많아질 수 있어 "
        "제한한다. 0 이하를 주면 상한 없이 전부 처리",
    )
    parser.add_argument(
        "--seed", type=int, default=None, help="재현 가능한 결과가 필요하면 지정"
    )
    return parser


if __name__ == "__main__":
    args = _build_arg_parser().parse_args()
    source_dir = args.source_dir or Path(settings.upload_dir)

    if args.from_messages:
        setup_test_video_data_from_messages(
            source_dir=source_dir,
            cctv_count=args.cctv_count,
            max_per_folder=args.max_per_folder,
            seed=args.seed,
            max_pairs=args.max_pairs if args.max_pairs > 0 else None,
        )
    else:
        if not args.start_date or not args.end_date:
            raise SystemExit(
                "--from-messages를 안 쓸 때는 --start-date/--end-date가 필수입니다."
            )
        if args.end_date < args.start_date:
            raise SystemExit("--end-date는 --start-date 이후(또는 같은 날)여야 합니다.")

        setup_test_video_data(
            start_date=args.start_date,
            end_date=args.end_date,
            source_dir=source_dir,
            cctv_count=args.cctv_count,
            max_per_folder=args.max_per_folder,
            region_codes=args.region_codes,
            seed=args.seed,
        )