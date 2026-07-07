from datetime import datetime

from sqlalchemy.orm import Session

from backend.db.models import Video, VideoDetail


class VideoRepository:
    def __init__(self, db: Session):
        self.db = db

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
