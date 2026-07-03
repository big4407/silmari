from datetime import datetime

from sqlalchemy.orm import Session

from backend.db.models import Video

class VideoRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, video: Video) -> Video:
        self.db.add(video)
        self.db.commit()
        self.db.refresh(video)
        return video

    def get_by_id(self, video_id: int) -> Video | None:
        return (
            self.db.query(Video)
            .filter(Video.id == video_id)
            .first()
        )

    def find_by_location_and_time(
        self,
        location: str,
        start_time: datetime,
        end_time: datetime,
    ) -> list[Video]:
        return (
            self.db.query(Video)
            .filter(
                Video.location == location,
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