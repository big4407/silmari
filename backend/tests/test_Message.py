"""
Message 테이블에 테스트용 데이터를 넣는다.

SN(일련번호)에 "T" 접두어를 붙여서(T00001, T00002 ...) 실제 API로 수집된 문자
(숫자 SN)와 한눈에 구분되게 한다.

test_place_videos.py --from-messages 모드가 Message 테이블을 그대로 읽어서
CCTV 폴더를 채우므로, rcptn_rgn_nm은 실제 Region 테이블에 있는 지역명과
일치해야 그쪽에서도 매칭이 된다 — 기본값은 흔한 예시 지역명이니, 실제 DB의
Region 데이터에 맞는 지역으로 --region을 바꿔서 쓰는 걸 권장한다.

운영 코드가 아니라 테스트용 스크립트라 tests/ 아래에 둔다. pytest가 자동
수집해서 실행할 test_* 함수는 없다 — `python -m` 으로 수동 실행한다
(test_place_videos.py/test_scheduler.py와 동일한 패턴).

사용 예:
  python -m backend.tests.test_Message
  python -m backend.tests.test_Message --count 5 --region "대전광역시 동구 가양동"
  python -m backend.tests.test_Message --region "서울특별시 강남구 역삼동" --region "부산광역시 해운대구 우동" \\
      --clear-existing
"""
from __future__ import annotations

import argparse
import random
from datetime import datetime, timedelta

from backend.db.database import SessionLocal
from backend.db.models import Message
from backend.repositories.message_repository import MessageRepository

# rcptn_rgn_nm 기본값 — 실제 Region 테이블 데이터와 안 맞으면 --region으로 덮어써야 함.
DEFAULT_REGIONS = [
    "대전광역시 동구",
    "서울특별시 강남구",
    "부산광역시 해운대구",
]

CLOTHING_SAMPLES = [
    "검은 패딩에 청바지 착용",
    "회색 후드티에 검은 바지 착용",
    "흰색 셔츠에 베이지색 바지 착용",
    "파란색 셔츠에 검은색 바지 착용",
    "빨간색 재킷에 회색 바지 착용",
]

NAME_SAMPLES = ["김OO", "이OO", "박OO", "최OO", "정OO"]


def build_test_message(index: int, region: str, base_dt: datetime) -> dict:
    """utils/message_filter.is_missing_person_message 조건(재해구분명=기타,
    실종 키워드 포함)에 맞는 문자 1건을 만든다 — 실제 실종문자와 같은 모양이라야
    나중에 이 데이터로 다른 걸 테스트할 때도 어긋나지 않는다."""
    name = random.choice(NAME_SAMPLES)
    clothing = random.choice(CLOTHING_SAMPLES)
    crt_dt = base_dt + timedelta(minutes=index)
    msg_cn = (
        f"[{region}] {name}(이)가 실종되었습니다. 인상착의: {clothing}. "
        f"목격 시 경찰서로 신고 바랍니다."
    )
    return {
        "sn": f"T{index:05d}",
        "crt_dt": crt_dt,
        "msg_cn": msg_cn,
        "rcptn_rgn_nm": region,
        "emrg_step_nm": "안전안내",
        "dst_se_nm": "기타",
        "reg_ymd": crt_dt.date(),
        "mdfcn_ymd": crt_dt.date(),
    }


def clear_test_messages(db) -> int:
    """SN이 T로 시작하는(=테스트로 넣은) 데이터만 지운다. 실제 API 수집분은 안 건드림."""
    deleted = (
        db.query(Message)
        .filter(Message.sn.like("T%"))
        .delete(synchronize_session=False)
    )
    db.commit()
    return deleted


def insert_test_messages(
    count: int = 10,
    regions: list[str] | None = None,
    clear_existing: bool = False,
) -> dict:
    regions = regions or DEFAULT_REGIONS
    base_dt = datetime.now()

    db = SessionLocal()
    try:
        repository = MessageRepository(db)

        if clear_existing:
            deleted = clear_test_messages(db)
            print(f"[테스트 문자 정리] SN이 T로 시작하는 기존 데이터 {deleted}건 삭제")

        inserted = 0
        skipped = 0
        for i in range(1, count + 1):
            region = regions[(i - 1) % len(regions)]
            data = build_test_message(i, region, base_dt)

            if repository.find_by_sn(data["sn"]):
                skipped += 1
                continue

            repository.insert(**data)
            inserted += 1

        print(f"[테스트 문자 삽입 완료] {inserted}건 삽입, {skipped}건은 이미 있어 건너뜀")
        return {"inserted": inserted, "skipped": skipped}
    finally:
        db.close()


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Message 테이블에 테스트용 실종 안내문자를 넣는다(SN에 T 접두어)."
    )
    parser.add_argument(
        "--count", type=int, default=10, help="넣을 테스트 문자 건수 (기본 10)"
    )
    parser.add_argument(
        "--region",
        action="append",
        dest="regions",
        help="rcptn_rgn_nm으로 쓸 지역명(반복 지정 가능, 여러 개 주면 순환 배정). "
        "안 주면 기본 예시 지역 3곳을 씀 — Region 테이블 실데이터와 맞는 지역명을 "
        "주는 걸 권장",
    )
    parser.add_argument(
        "--clear-existing",
        action="store_true",
        help="넣기 전에 SN이 T로 시작하는 기존 테스트 데이터를 먼저 삭제",
    )
    return parser


if __name__ == "__main__":
    args = _build_arg_parser().parse_args()
    insert_test_messages(
        count=args.count,
        regions=args.regions,
        clear_existing=args.clear_existing,
    )
