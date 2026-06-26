from fashion_clip.fashion_clip import FashionCLIP
from pathlib import Path
import numpy as np
import json

model = FashionCLIP("fashion-clip")

def load_embedding_data(embedding_dir:str):
    """
        저장된 이미지 임베딩과 메타데이터를 불러온다.
    """
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