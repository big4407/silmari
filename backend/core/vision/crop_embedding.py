# data/results/unique_persons/
# → 대표 이미지들 읽기

# FashionCLIP
# → 각 이미지 임베딩 생성

# data/results/embeddings/
# ├─ image_embeddings.npy
# └─ metadata.json
from fashion_clip.fashion_clip import FashionCLIP
from pathlib import Path
import numpy as np
import json



def get_image_paths(image_dir):
    """
    동일인물 제거를한 unique_persons 폴더에서 jpg 이미지 경로 목록 반환
    """
    image_dir = Path(image_dir)
    image_paths = sorted(image_dir.glob("*.jpg"))
    return image_paths

def create_image_embeddings(image_paths):
    """
        이미지 경로 목록을 FashionCLIP 이미지 임베딩으로 변환
    """
    fclip = FashionCLIP("fashion-clip")
    path_strings = [str(path) for path in image_paths]
    embeddings = fclip.encode_images(path_strings, batch_size=32)
    return embeddings

def normalize_embeddings(embeddings):
    """
        코사인 유사도 계산용으로 정규화된 임베딩 반환:
    """
    norms = np.linalg.norm(
        embeddings,
        axis=1,
        keepdims=True
    )
    return embeddings / norms

def make_metadata(image_paths):
    """
        index, group_id, image_path 목록 생성
    """
    metadata = []
    for index, image_path in enumerate(image_paths):
        metadata.append({
            "index": index,
            "image_path": str(image_path)
            # crop_id,
            # embedding,
            # video_id,
            # frame_number,
            # timestamp,
            # location,
            # person_index
        })
    return metadata

def save_embedding_data(embeddings, metadata, save_dir):
    """
        npy와 json 파일 저장
    """
    save_dir = Path(save_dir)
    save_dir.mkdir(parents=True, exist_ok=True)

    embedding_path = save_dir / "image_embeddings.npy"
    metadata_path = save_dir / "metadata.json"

    np.save(embedding_path, embeddings)

    with open(metadata_path, "w", encoding="utf-8") as file:
        json.dump(
            metadata,
            file,
            ensure_ascii=False,
            indent=4
        )


def analyze_unique_persons(image_dir: str, save_dir: str):
    image_paths = get_image_paths(image_dir)

    embeddings = create_image_embeddings(image_paths)

    normalized_embeddings = normalize_embeddings(embeddings)

    metadata = make_metadata(image_paths)

    save_embedding_data(
        normalized_embeddings,
        metadata,
        save_dir
    )

if __name__ == "__main__":
    analyze_unique_persons("data/results/unique_persons", "data/results/embeddings")