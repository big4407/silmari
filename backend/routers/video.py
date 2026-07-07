import shutil
from pathlib import Path

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from backend.db.database import get_db
from backend.services.video_service import VideoService
# (
#     frame_extract,
#     person_detect,
#     check_same_person,
#     create_image_embeddings,
#     get_image_paths,
#     normalize_embeddings,
#     make_metadata,
#     save_embedding
# )


router = APIRouter()


class VideoProcessRequest(BaseModel):
    video_path: str
    every_nth: int = 5


@router.post("/process")
def process_video(
    data: VideoProcessRequest,
    db: Session = Depends(get_db)
    ):
    service = VideoService(db)
    video_path = Path(data.video_path)

    if not video_path.exists():
        raise HTTPException(
            status_code=404,
            detail="영상 파일을 찾을 수 없습니다.",
        )

    try:
        service.process_videos([str(video_path)])

        return {
        "message": "영상 처리가 완료되었습니다.",
        "video_path": str(video_path),
        }

    except HTTPException:
        raise

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"영상 처리 중 오류가 발생했습니다: {str(error)}",
        )
    
    finally:
        folder_path = Path("data/results/frames")
        if folder_path.exists():
            for item in folder_path.iterdir():
                if item.is_file():
                    item.unlink()
                elif item.is_dir():
                    shutil.rmtree(item)

        folder_path = Path("data/results/detected")
        if folder_path.exists():
            for item in folder_path.iterdir():
                if item.is_file():
                    item.unlink()
                elif item.is_dir():
                    shutil.rmtree(item)        