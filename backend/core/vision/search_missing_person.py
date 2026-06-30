"""
FashionCLIP 기반 텍스트→이미지 유사도 검색 (오프라인 임베딩 비교).

[용도] CCTV에서 추출·중복 제거된 인물 크롭(data/results/embeddings)을
       안내문자 인상착의 텍스트 쿼리와 코사인 유사도로 랭킹한다.
[연계] crop_embedding.py(임베딩 생성) · check_same_person.py(동일인 병합)
[상태] search_similar_images() 반환값 미구현 — matcher.py 쪽이 실제 탐지에 사용됨
"""
from fashion_clip.fashion_clip import FashionCLIP
from pathlib import Path
import numpy as np
import json

model = FashionCLIP("fashion-clip")

def load_embedding_data(embedding_dir:str):
    """data/results/embeddings/ 에 저장된 .npy 임베딩 + metadata.json 로드."""
    embedding_dir = Path(embedding_dir)
    embedding_path = embedding_dir / "image_embeddings.npy"
    metadata_path = embedding_dir / "metadata.json"

    image_embeddings = np.load(embedding_path)
    with open(metadata_path, "r", encoding="utf-8") as file:
        metadata = json.load(file)
    return image_embeddings, metadata

def create_text_embedding(model, query):
    """
        검색에 사용한 텍스트를 임베딩된 사람 크롭 이미지와 비교하여 찾기 위하여 임베딩한다.
    """
    text_embedding = model.encode_text([query], batch_size=1)
    text_embedding = text_embedding / np.linalg.norm(
        text_embedding,
        axis=1,
        keepdims=True
    )
    return text_embedding

def search_similar_images(
    image_embeddings,
    text_embedding,
    metadata,
    top_k=10
):
    """
        텍스트 임베딩과 이미지 임베딩을 비교하여 점수를 매겨 순위가 높은 이미지를 가져온다.
    """
    similarities = image_embeddings @ text_embedding[0]
    top_indices = np.argsort(similarities)[::-1][:top_k]


if __name__ == "__main__" :
    image_embeddings, metadata = load_embedding_data("data/results/embeddings")
    text_embedding = create_text_embedding()