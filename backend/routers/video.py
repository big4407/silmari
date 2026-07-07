import shutil
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
# from backend.services.video_service import (
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
def process_video(data: VideoProcessRequest):
    video_path = Path(data.video_path)

    if not video_path.exists():
        raise HTTPException(
            status_code=404,
            detail="영상 파일을 찾을 수 없습니다.",
        )

    try:
        # 1. 영상 프레임 추출
        # frame_extract(
        #     video_path=str(video_path),
        #     every_nth=data.every_nth,
        # )

        # frame_path = "data/results/frames"

        # # 2. 프레임에서 사람 탐지 및 crop 저장
        # person_detect(frame_path)

        # detected_path = "data/results/detected"

        # # 3. 동일 인물 그룹화 및 대표 이미지 저장
        # check_same_person(detected_path)

        # unique_person_path = "data/results/unique_persons"

        # # 4. 대표 이미지 임베딩 생성
        # image_paths = get_image_paths(unique_person_path)

        # if not image_paths:
        #     raise HTTPException(
        #         status_code=404,
        #         detail="임베딩할 대표 이미지가 없습니다.",
        #     )

        # embeddings = create_image_embeddings(image_paths)
        # normalized_embeddings = normalize_embeddings(embeddings)
        # metadata_list = make_metadata(image_paths)

        # # 5. ChromaDB 저장
        # for index, (embedding, metadata) in enumerate(
        #     zip(normalized_embeddings, metadata_list)
        # ):
        #     embedding_id = f"{video_path.stem}_{index}"

        #     save_embedding(
        #         id=embedding_id,
        #         embedding=embedding.tolist(),
        #         metadata=metadata,
        #     )

        # return {
        #     "message": "영상 처리가 완료되었습니다.",
        #     "video_path": str(video_path),
        #     "saved_embedding_count": len(image_paths),
        # }
        pass

    except HTTPException:
        raise

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"영상 처리 중 오류가 발생했습니다: {str(error)}",
        )

    finally:
        folder_path = Path("data/results/frames")
        for item in folder_path.iterdir():
            if item.is_file():
                item.unlink()
            elif item.is_dir():
                shutil.rmtree(item)

        folder_path = Path("data/results/detected")
        for item in folder_path.iterdir():
            if item.is_file():
                item.unlink()
            elif item.is_dir():
                shutil.rmtree(item)
