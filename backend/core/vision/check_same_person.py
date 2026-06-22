from torchreid.utils import FeatureExtractor
from pathlib import Path
import torch.nn.functional as F
import os

image_dir = Path("data/results/detected")
save_dir = Path("data/results/unique_persons")
save_dir.mkdir(parents=True, exist_ok=True)
extractor = FeatureExtractor(
    model_name="osnet_x1_0",
    device="cpu"
)

image_paths = []
for ext in ["*.jpg"]:
    image_paths.extend(image_dir.glob(ext))
image_paths = sorted(image_paths)
image_paths = [str(path) for path in sorted(image_paths)]

if not image_paths:
    print("사람 crop 이미지가 없습니다.")
else:
    features = extractor(image_paths)


groups = [
    {
        "representative_index": 0,
        "members": [0]
    }
]

for i in range(1, len(features)):
    best_group = None
    best_similarity = 0
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
# for i in range(len(features)):
#     if i in checked_number:
#         continue
#     for j in range(i + 1, len(features)):
#         if j in checked_number:
#             continue
#         similarity = F.cosine_similarity(
#             features[i].unsqueeze(0),
#             features[j].unsqueeze(0)
#         ).item()
#         if similarity > .7:

#             checked_number.append(j)
#             pass
#         else:
#             checked_image_paths.append(image_paths[j])
#             checked_number.append(j)
        # print(image_paths[i], image_paths[j], similarity)
        #이미지 첫번째는 바로 저장한다,
        #이미지 두번째 부터 10번째까지 있다고 가정하겠다
        # 두번째부터 첫번재 이미지와 비교후 0.7이상이면 후보군에 넣고 틀리면 두번째 unique person이 된다.
        # 만약 세번째가 첫번째와 두번째와 0.7 이라면 어떻게 해야하나 첫번째 유사후보군에 넣고 다음 반복부터 제외해야하나 아니면
        # 두번째 unique person한테도 유사후보군으로 넣어야하나

        # 첫번재 이미지는 uniqueperson
        # 두번째 이미지는 unique person
        # 세번째 이미지도 첫번재와 비교해서 unique person 이라면
        # 두번재와 세번째는 유사한 사람일 수도 있잖은가 이런걸 어떻게 해결하면 좋은가
        # 그러니깐 i반복문에서 unique person은 한명만 add될 수 있게 해야하는가