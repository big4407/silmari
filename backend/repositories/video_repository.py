from datetime import datetime

from sqlalchemy import desc, func, select, update, exists
from sqlalchemy.orm import Session

from backend.db.models import Video, VideoDetail


class VideoRepository:
    def __init__(self, db: Session):
        self.db = db

    def count_with_region_code(self) -> int:
        return (
            self.db.scalar(
                select(func.count())
                .select_from(Video)
                .where(Video.region_code.isnot(None))
            )
            or 0
        )

    def count_all(self) -> int:
        return self.db.scalar(select(func.count()).select_from(Video)) or 0

    def count_distinct_regions(self) -> int:
        """영상이 1건이라도 있는 지역 수(=수집이 실제로 이뤄진 지역)."""
        return (
            self.db.scalar(
                select(func.count(func.distinct(Video.region_code))).where(
                    Video.region_code.isnot(None)
                )
            )
            or 0
        )

    def get_region_coverage(self) -> list[dict]:
        """region_code별 CCTV 대수·영상 파일 수 집계 — 지역별 현황 화면용.

        용량·시간대 커버리지는 Video 테이블에 그 데이터 자체가 없어서(파일
        크기 컬럼 없음, 파일명에 시각 정보 없음) 여기서 다루지 않는다.
        """
        rows = (
            self.db.query(
                Video.region_code,
                func.count(func.distinct(Video.cctv_serial_no)).label("cctv_count"),
                func.count(Video.id).label("video_count"),
            )
            .filter(Video.region_code.isnot(None))
            .group_by(Video.region_code)
            .all()
        )
        return [
            {
                "region_code": region_code,
                "cctv_count": cctv_count,
                "video_count": video_count,
            }
            for region_code, cctv_count, video_count in rows
        ]

    def get_daily_summary(
        self, page: int, per_page: int
    ) -> tuple[list[dict], int]:
        """recorded_at(촬영일자)별 영상 현황 — "일자별 이력" 화면용.

        별도 작업 기록 테이블 없이 Video 테이블만으로 만든다. 그래서 "그 날
        시도했지만 하나도 성공 못 한 영상"이나 "건너뛴 개수"는 여기 안 잡힌다
        — Video row는 처리 성공한 것만 최종적으로 남기 때문에, 이 표는
        "그 날짜로 실제 등록된 영상"만 보여준다는 걸 감안해야 한다.
        """
        base_query = self.db.query(Video.recorded_at).filter(
            Video.recorded_at.isnot(None)
        )
        total = base_query.distinct().count()

        rows = (
            self.db.query(
                Video.recorded_at,
                func.count(Video.id).label("video_count"),
                func.count(func.distinct(Video.region_code)).label("region_count"),
                func.min(Video.created_at).label("first_indexed_at"),
                func.max(Video.created_at).label("last_indexed_at"),
            )
            .filter(Video.recorded_at.isnot(None))
            .group_by(Video.recorded_at)
            .order_by(desc(Video.recorded_at))
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )
        items = [
            {
                "target_date": recorded_at,
                "video_count": video_count,
                "region_count": region_count,
                "first_indexed_at": first_indexed_at,
                "last_indexed_at": last_indexed_at,
            }
            for recorded_at, video_count, region_count, first_indexed_at, last_indexed_at in rows
        ]
        return items, total

    def unlink_all_region_codes(self) -> int:
        """모든 video.region_code 를 NULL 처리한다 (region 테이블 전체 삭제 전 정리용).

        반환값: 영향받은 row 수.
        """
        result = self.db.execute(
            update(Video).where(Video.region_code.isnot(None)).values(region_code=None)
        )
        return result.rowcount or 0

    def create(self, video: Video) -> Video:
        self.db.add(video)
        self.db.commit()
        self.db.refresh(video)
        return video

    def create_detail(self, video_detail: VideoDetail) -> VideoDetail:
        self.db.add(video_detail)
        self.db.commit()
        self.db.refresh(video_detail)
        return video_detail

    def get_by_id(self, video_id: int) -> Video | None:
        return self.db.query(Video).filter(Video.id == video_id).first()

    def get_by_file_path(self, file_path: str) -> Video | None:
        """file_path 로 영상 1건 조회 — 중복 처리 방지용."""
        return self.db.query(Video).filter(Video.file_path == file_path).first()

    def exists_by_file_path(self, file_path: str) -> bool:
        """해당 경로의 영상이 이미 처리(저장)되었는지 여부."""
        return (
            self.db.query(Video.id).filter(Video.file_path == file_path).first()
            is not None
        )

    def find_by_region_and_time(
        self,
        region_code: str,
        start_time: datetime,
        end_time: datetime,
    ) -> list[Video]:
        return (
            self.db.query(Video)
            .filter(
                Video.region_code == region_code,
                Video.recorded_at >= start_time,
                Video.recorded_at <= end_time,
            )
            .all()
        )

    def find_ids(
        self,
        region_codes: list[str] | None = None,
        start_date=None,
        end_date=None,
    ) -> list[int]:
        """지역 코드 목록·기간으로 video.id 를 좁혀서 조회한다.

        세 조건 모두 optional — 아무 조건도 없으면 빈 리스트를 돌려준다
        (전체 대상 여부는 호출 측에서 판단; 여기서 암묵적으로 "전체"를
        의미하지 않도록 명시적으로 빈 리스트를 반환한다).
        """
        query = self.db.query(Video.id)
        has_filter = False

        if region_codes:
            query = query.filter(Video.region_code.in_(region_codes))
            has_filter = True
        if start_date:
            query = query.filter(Video.recorded_at >= start_date)
            has_filter = True
        if end_date:
            query = query.filter(Video.recorded_at <= end_date)
            has_filter = True

        if not has_filter:
            return []

        return [row[0] for row in query.all()]

    def exists_by_region_and_period(
        self,
        *,
        region_code: str,
        start_at: datetime,
        end_at: datetime,
    ) -> bool:
        """
        해당 지역과 촬영 기간에 영상이 하나 이상 존재하는지 확인한다.
        """

        stmt = select(
            exists().where(
                Video.region_code == region_code,
                Video.recorded_at >= start_at,
                Video.recorded_at < end_at,
            )
        )

        return bool(self.db.scalar(stmt))