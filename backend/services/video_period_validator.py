"""
사용자가 입력한 지역과 기간에 검색 가능한 영상이 존재하는지 검증하는 모듈
"""

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from enum import Enum

from backend.repositories.video_repository import VideoRepository


class VideoPeriodValidationStatus(str, Enum):
    """
    영상 기간 검증 결과 상태
    """

    VALID = "valid"
    INVALID_RANGE = "invalid_range"
    VIDEO_NOT_FOUND = "video_not_found"


@dataclass(frozen=True)
class VideoPeriodValidationResult:
    """
    영상 기간 검증 결과

    Attributes:
        status:
            검증 결과 상태

        start_at:
            영상 조회에 사용한 시작 일시

        end_at:
            영상 조회에 사용한 종료 일시.
            종료 날짜의 다음 날 00:00이며 조회 시 미만(<) 조건으로 사용한다.
    """

    status: VideoPeriodValidationStatus
    start_at: datetime | None = None
    end_at: datetime | None = None

    @property
    def is_valid(self) -> bool:
        """
        유효한 지역 및 기간인지 반환한다.
        """

        return self.status == VideoPeriodValidationStatus.VALID


class VideoPeriodValidator:
    """
    특정 지역과 기간에 검색 가능한 영상이 존재하는지 검증한다.

    날짜 범위는 다음과 같은 반개방 구간으로 변환한다.

        start_at <= recorded_at < end_at

    예를 들어 2026-07-01부터 2026-07-03까지 조회하는 경우:

        start_at = 2026-07-01 00:00:00
        end_at   = 2026-07-04 00:00:00

    따라서 2026-07-03에 촬영된 영상도 모두 포함된다.
    """

    def __init__(self, video_repository: VideoRepository):
        self.video_repository = video_repository

    def validate(
        self,
        *,
        region_code: str,
        start_date: date,
        end_date: date,
    ) -> VideoPeriodValidationResult:
        """
        지역과 기간에 해당하는 영상의 존재 여부를 검증한다.

        Args:
            region_code:
                지역 검증을 통해 확정된 지역 코드

            start_date:
                사용자가 입력한 조회 시작일

            end_date:
                사용자가 입력한 조회 종료일

        Returns:
            VideoPeriodValidationResult:
                VALID:
                    입력 기간이 올바르고 해당 지역과 기간에 영상이 존재함

                INVALID_RANGE:
                    시작일이 종료일보다 늦음

                VIDEO_NOT_FOUND:
                    입력 기간은 올바르지만 해당 지역과 기간에 영상이 없음
        """

        if start_date > end_date:
            return VideoPeriodValidationResult(
                status=VideoPeriodValidationStatus.INVALID_RANGE,
            )

        start_at, end_at = self._to_datetime_range(
            start_date=start_date,
            end_date=end_date,
        )

        video_exists = self.video_repository.exists_by_region_and_period(
            region_code=region_code,
            start_at=start_at,
            end_at=end_at,
        )

        if not video_exists:
            return VideoPeriodValidationResult(
                status=VideoPeriodValidationStatus.VIDEO_NOT_FOUND,
                start_at=start_at,
                end_at=end_at,
            )

        return VideoPeriodValidationResult(
            status=VideoPeriodValidationStatus.VALID,
            start_at=start_at,
            end_at=end_at,
        )

    @staticmethod
    def _to_datetime_range(
        *,
        start_date: date,
        end_date: date,
    ) -> tuple[datetime, datetime]:
        """
        날짜 범위를 영상 조회에 사용할 datetime 범위로 변환한다.

        종료 시각은 종료일의 다음 날 00:00으로 변환하여
        Repository에서 `< end_at` 조건으로 조회할 수 있도록 한다.
        """

        start_at = datetime.combine(start_date, time.min)
        end_at = datetime.combine(
            end_date + timedelta(days=1),
            time.min,
        )

        return start_at, end_at


if __name__ == "__main__":
    from datetime import date

    from backend.db.database import SessionLocal
    from backend.repositories.video_repository import VideoRepository

    db = SessionLocal()

    try:
        validator = VideoPeriodValidator(video_repository=VideoRepository(db))

        test_cases = [
            {
                "region_code": "1100000000",
                "start_date": date(2026, 7, 9),
                "end_date": date(2026, 7, 10),
            },
            {
                "region_code": "1100000000",
                "start_date": date(2026, 7, 1),
                "end_date": date(2026, 7, 2),
            },
            {
                "region_code": "1111054000",
                "start_date": date(2026, 7, 9),
                "end_date": date(2026, 7, 10),
            },
            {
                "region_code": "1100000000",
                "start_date": date(2026, 7, 10),
                "end_date": date(2026, 7, 9),
            },
        ]

        for i, case in enumerate(test_cases, start=1):
            result = validator.validate(**case)

            print("=" * 60)
            print(f"Test {i}")
            print(case)
            print(f"status   : {result.status}")
            print(f"is_valid : {result.is_valid}")
            print(f"start_at : {result.start_at}")
            print(f"end_at   : {result.end_at}")

    finally:
        db.close()
