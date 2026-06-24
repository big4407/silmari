# matcher파일 동일인물 검증 기능으로 분리된 이미지를 text query문과 비교해서 점수를 뽑아내 상위 5명을 가져온다.
from fashion_clip.fashion_clip import FashionCLIP
from pathlib import Path
import numpy as np
import os


image_dir = Path("data/results/unique_persons")
image_dir.mkdir(parents=True, exist_ok=True)
texts = [
    "a person wearing white shirt and gray pants"
]
image_paths = []
for ext in ["*.jpg"]:
    image_paths.extend(image_dir.glob(ext))
image_paths_str = [str(path) for path in image_paths]


fclip = FashionCLIP("fashion-clip")

image_embeddings = fclip.encode_images(image_paths_str, batch_size=32)
text_embeddings = fclip.encode_text(texts, batch_size=32)
image_embeddings /= np.linalg.norm(
    image_embeddings,
    axis =1,
    keepdims=True
)
text_embeddings /= np.linalg.norm(
    text_embeddings,
    axis =1,
    keepdims=True
)
similarities = image_embeddings @ text_embeddings[0]

top_k = 5
top_indices = np.argsort(similarities)[::-1][:top_k]

candidates = []

for rank, index in enumerate(top_indices, start=1):
    candidates.append({
        "rank":rank,
        "image_path": image_paths[index],
        "score": float(similarities[index])
    })

print(candidates)