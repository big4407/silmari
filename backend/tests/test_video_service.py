from pathlib import Path

from backend.services.video_service import VideoService
from backend.db.database import Base, SessionLocal, engine, get_db, get_chromadb
from backend.core.config import settings


def get_video_files(folder_path):
    # 탐색할 폴더 경로 설정
    target_dir = Path(folder_path)

    # 찾고자 하는 영상 확장자 목록 정의 (대소문자 구분 없음)
    video_extensions = {".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm"}
    # 폴더 내 모든 파일 탐색 (하위 폴더까지 포함하려면 rglob, 현재 폴더만은 glob)

    video_paths = [
        str(file.resolve())
        for file in target_dir.rglob("*")
        if file.suffix.lower() in video_extensions
    ]

    return video_paths


def test_logic():
    service = VideoService(next(get_db()))
    video_paths = get_video_files(
        Path(settings.cctv_data_dir) / "41110" / "20260628" / "CCTV1234"
    )

    service.process_videos(video_paths)


if __name__ == "__main__":
    test_logic()
