import chromadb
from backend.core.vision.chroma_db import get_collection
from fashion_clip.fashion_clip import FashionCLIP
import numpy as np

fclip = FashionCLIP("fashion-clip")
collection = get_collection()

def search_embedding(query, n=5,):
    query_embedding = fclip.encode_text(
        [query], 
        batch_size=1
    )
    query_embedding = query_embedding / np.linalg.norm(
        query_embedding,
        axis=1,
        keepdims=True
    )
    result = collection.query(
        query_embeddings = query_embedding.tolist(),
        n_results=n
    )
    return result

if __name__ == "__main__":
    query = input("쿼리문을 입력하세요:")
    result = search_embedding(query)
    print(result)