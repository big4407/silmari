"""VideoService 통합 테스트 — 실제 모델·영상으로 전체 파이프라인 실행.

⚠️ 실행 조건 (단위 테스트와 달리 무거움):
  - YOLO / FashionCLIP / torchreid 모델이 설치·다운로드되어 있어야 함
  - 실제 CCTV 영상이 아래 경로 규칙으로 존재해야 함:
      {cctv_data_dir}/{region_code}/{YYYYMMDD}/{cctv_serial_no}/*.mp4
  - MySQL·Chroma 연결이 설정되어 있어야 함

CI 가 아니라 로컬에서 수동으로 돌리는 스모크 테스트다.
빠른 로직 검증은 test_video_service.py(mock) 를 쓴다.
"""
from pathlib import Path

from backend.services.video_service import VideoService
from backend.db.database import get_db
from backend.core.config import settings


def get_video_files(folder_path: str) -> list[str]:
    """폴더(하위 포함)에서 영상 파일 경로 목록을 수집."""
    target_dir = Path(folder_path)
    video_extensions = {".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm"}
    return [
        str(file.resolve())
        for file in target_dir.rglob("*")
        if file.suffix.lower() in video_extensions
    ]


def run_smoke_test():
    service = VideoService(next(get_db()))

    # 경로 규칙: region_code/YYYYMMDD/cctv_serial_no/*.mp4
    folder = Path(settings.cctv_data_dir) / "1114052000" / "20260628" / "CCTV1234"
    video_paths = get_video_files(str(folder))
    if not video_paths:
        print(f"[스킵] 영상이 없습니다: {folder}")
        return

    print(f"[처리] {len(video_paths)}개 영상")
    service.process_videos(video_paths)

    # Chroma 저장 확인 — video.id 로 조회 (embedding_id 불필요)
    # 실제 저장된 video id 로 바꿔서 확인
    sample = service.get_embeddings_by_video_id(1)
    print("[Chroma 조회 결과]", sample)


if __name__ == "__main__":
    run_smoke_test()
