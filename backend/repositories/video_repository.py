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

    def create_detail(self, video_detail:VideoDetail) -> VideoDetail:
        self.db.add(video_detail)
        self.db.commit()
        self.db.refresh(video_detail)
        return video_detail
    
    def get_by_id(self, video_id: int) -> Video | None:
        return (
            self.db.query(Video)
            .filter(Video.id == video_id)
            .first()
        )
    def update_embedding_id(
        self,
        video: Video,
        embedding_id: str,
        ) -> Video:
        video.embedding_id = embedding_id
        self.db.commit()
        self.db.refresh(video)
        return video

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

    def update_status(
        self,
        video: Video,
        status: str,
    ) -> Video:
        video.status = status

        self.db.commit()
        self.db.refresh(video)

        return video