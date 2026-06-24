from torchreid.utils import FeatureExtractor
from pathlib import Path
import torch.nn.functional as F
import os
import shutil
import json

image_dir = Path("data/results/detected")
save_dir = Path("data/results/unique_persons")
save_dir.mkdir(parents=True, exist_ok=True)
json_path = save_dir / "group_data.json"
extractor = FeatureExtractor(
    model_name="osnet_x1_0",
    device="cpu"
)

image_paths = []
for ext in ["*.jpg"]:
    image_paths.extend(image_dir.glob(ext))
image_paths = sorted(image_paths)

if not image_paths:
    print("사람 crop 이미지가 없습니다.")
    raise SystemExit

features = extractor([str(path) for path in image_paths])


groups = [
    {
        "representative_index": 0,
        "members": [0]
    }
]

for i in range(1, len(features)):
    best_group = None
    best_similarity = -1
    for group in groups:
        representative_index = group["representative_index"]

        similarity = F.cosine_similarity(
            features[i].unsqueeze(0),
            features[representative_index].unsqueeze(0)
        ).item()
        if similarity > best_similarity:
            best_similarity = similarity
            best_group = group
        
    if best_similarity >= 0.7:
        best_group["members"].append(i)
    else:
        groups.append({
            "representative_index": i,
            "members": [i]
        })

group_data = {}
for group_number, group in enumerate(groups, start=1):
    representative_index = group["representative_index"]
    source_path = image_paths[representative_index]
    save_path = save_dir / f"group_{group_number:04d}{source_path.stem}{source_path.suffix}"
    shutil.copy2(source_path, save_path)
    group_data[f"group_{group_number:04d}"] = {
        "representative": str(save_path),
        "members": [
            str(image_paths[index]) for index in group["members"]
        ]
    }

with open(json_path, "w", encoding="utf-8") as file:
    json.dump(
        group_data,
        file,
        ensure_ascii=False,
        indent=4
    )