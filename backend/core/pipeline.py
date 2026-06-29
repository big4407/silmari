from backend.core.llm.chain import run_alert_parse_chain
from backend.core.vision.frame_extractor import extract_frames
from backend.core.vision.matcher import match_persons_in_frame
from typing import Optional


def run_detection_pipeline(
    video_path: str, sms_text: str, reference_img_path: Optional[str] = None
) -> dict:
    alert_info = run_alert_parse_chain(sms_text)
    detections = []

    for frame_idx, frame, timestamp_sec in extract_frames(video_path):
        detections.extend(
            match_persons_in_frame(
                frame,
                frame_idx,
                timestamp_sec,
                alert_info.model_dump(),
                reference_img_path,
            )
        )

    return {
        "sms_info": alert_info,
        "total_detections": len(detections),
        "face_recognition_used": reference_img_path is not None,
        "detections": detections,
    }

# 엄태윤 파이프라인
from backend.core.vision.frame_extractor import frame_extract
from backend.core.vision.person_detector import person_detect
from backend.core.vision.check_same_person import check_same_person
from backend.core.vision.crop_embedding import *
from backend.core.vision.search_embedding import search_embedding
def detect_missing_person_pipeline(
        query:str,
        video_path:str="data/CCTV/output_video_1_1_1.mp4", 
        frame_interval:int=5,
        frame_path:str="data/results/frames",
        detected_path:str="data/results/detected",
        unique_person_path:str="data/results/unique_persons",
        max_results:int=5
):
    frame_extract(video_path, frame_interval)
    person_detect(frame_path)
    check_same_person(detected_path)
    image_paths = get_image_paths(unique_person_path)
    embeddings = create_image_embeddings(image_paths)
    normalized_embeddings = normalize_embeddings(embeddings)
    metadatas = make_metadata(image_paths)
    for image_path, embedding, metadata in zip(image_paths, normalized_embeddings, metadatas):
        save_embedding(
            id = image_path.stem,
            embedding = embedding.tolist(),
            metadata = metadata
        )
    result = search_embedding(query, max_results)
    ids = result["ids"][0]
    metadatas = result["metadatas"][0]
    distances = result["distances"][0]

    search_results = []
    for rank, (person_id, metadata, distance) in enumerate(
        zip(ids, metadatas, distances),
        start=1
        ):
        search_results.append({
            "rank": rank,
            "id": person_id,
            "image_path": metadata["image_path"],
            "distance": distance
        })
    return search_results

if __name__ == "__main__":
    query = input("착의정보를 입력하세요:")
    result = detect_missing_person_pipeline(query)
    print(result)