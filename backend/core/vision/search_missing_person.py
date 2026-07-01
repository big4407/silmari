from fashion_clip.fashion_clip import FashionCLIP
from pathlib import Path
import numpy as np
import json


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
    
    results = []

    for rank, index in enumerate(top_indices, start=1):
        results.append({
            "rank": rank,
            "score": float(similarities[index]),
            "image_path": metadata[index]["image_path"]
        })
    return results

def search_person(model, query, embedding_dir, top_k=5):
    image_embeddings, metadata = load_embedding_data(embedding_dir)
    text_embedding = create_text_embedding(model, query)

    return search_similar_images(
        image_embeddings,
        text_embedding,
        metadata,
        top_k
    )

if __name__ == "__main__" :
    fclip = FashionCLIP("fashion-clip")
    query = input("원하는 사람의 복장을 적으세요: ", )
    embedding_dir = "data/results/embeddings"
    results = search_person(
        fclip,
        query,
        embedding_dir,
        5
    )
    print(results)