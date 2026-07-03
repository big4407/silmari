import cv2
from typing import Generator, Tuple
import numpy as np
import os
from pathlib import Path
from ultralytics import YOLO
from backend.core.config import settings
from torchreid.utils import FeatureExtractor
import torch.nn.functional as F
import shutil
import json
from fashion_clip.fashion_clip import FashionCLIP
from backend.db.database import get_chromadb
from sqlalchemy.orm import Session
from backend.repositories.video_repository import VideoRepository

_model_path = Path(settings.yolo_model_path)
model = YOLO(str(_model_path) if _model_path.exists() else "yolov8n.pt")

class VideoService:
    def __init__(self, db:Session):
        self.db = db
        self.repository = VideoRepository(db)        
    


# ──────────────────────────────────────────────────────────────────────────
# 기능 함수
# frame_extract / 
# ──────────────────────────────────────────────────────────────────────────


    def frame_extract(
            video_path:str, every_nth: int = 5
    ):
        cap = cv2.VideoCapture(video_path)
        path = Path(video_path)
        video_name = path.stem

        if not cap.isOpened():
            print("오류: 영상을 열지 못했습니다.")
            exit()

        save_dir = Path("data/results/frames")
        save_dir.mkdir(parents=True, exist_ok=True)

        fps = cap.get(cv2.CAP_PROP_FPS)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total_frame = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        print(fps, width, height, total_frame)

        positions = [
            i * int(fps)
            for i in range(int(total_frame / fps))
            if i % every_nth == 0
        ]

        saved_count = 0

        for idx, pos in enumerate(positions, 1):
            cap.set(cv2.CAP_PROP_POS_FRAMES, pos)

            ret, frame = cap.read()

            if ret:
                seconds = int(pos / fps)
                save_path = os.path.join(save_dir, f"{video_name}_frame_{seconds:05d}s.jpg")
                success = cv2.imwrite(save_path, frame)

                if success:
                    saved_count += 1
                else:
                    print(f"저장 실패: {save_path}")

        # ──────────────────────────────────────────────────────────────────────────
        # db 에 저장하는 로직 생성
        # ──────────────────────────────────────────────────────────────────────────

        # Video 테이블에 데이터 저장하고
        # self.repository.VideoCreate(변수 이것저것)
        # Video Detail 테이블에 데이터 저장하고
        # self.repository.VideoDetailCreate(변수 이것저것)

        # return 성공했는지 안했는지 뭐이런거

        cap.release()
        print(f"저장된 프레임 수: {saved_count}")


    def person_detect(frame_path:str):
        "폴더 path를 주면 해당 폴더의 모든 frame에 대해 사람 식별함"
        image_dir = Path(frame_path)
        save_dir = Path("data/results/detected")

        save_dir.mkdir(parents=True, exist_ok=True)
        image_paths = []

        annotated_dir = Path("data/results/annotated_frames")
        annotated_dir.mkdir(parents=True, exist_ok=True)
        for ext in ["*.jpg"]:
            image_paths.extend(image_dir.glob(ext))

        image_paths = sorted(image_paths)

        results = model.predict(source=image_paths, conf=0.4, save=False, classes=0)
        print(results[0])


        for image_path, r in zip(image_paths, results):
            frame = cv2.imread(str(image_path))
            if frame is None:
                continue
            for person_idx, box in enumerate(r.boxes, 1):
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy().astype(int)

                confidence = float(box.conf[0].cpu().item())
                label = f"person {confidence:.2f}"
                person_crop = frame[y1:y2, x1:x2]
                
                save_path = save_dir / f"{image_path.stem}_person_{person_idx}.jpg"
                cv2.imwrite(str(save_path), person_crop)


                cv2.rectangle(
                    frame,
                    (x1, y1),
                    (x2, y2),
                    (0, 255, 0),
                    2
                )

                cv2.putText(
                    frame,
                    label,
                    (x1, max(y1 - 10, 20)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (0, 255, 0),
                    2
                )
            annotated_save_path = annotated_dir / image_path.name
            cv2.imwrite(str(annotated_save_path), frame)
        

    def check_same_person(detected_path:str):
        image_dir = Path(detected_path)
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


# crop embedding------------------------------------------------------
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
                # "crop_id"
                # embedding,
                # video_id,
                # frame_number,
                # timestamp,
                # location,
                # person_index
            })
        return metadata

    

# ──────────────────────────────────────────────────────────────────────────
# DB 접근 함수
# crop_embedding / 
# ──────────────────────────────────────────────────────────────────────────
    def save_embedding(id, embedding, metadata):
        collection = get_chromadb()
        collection.upsert(
            ids=[id],
            embeddings=[embedding],
            metadatas=[metadata]
        )


    def crop_embedding(self, image_dir):
        image_paths = self.get_image_paths(image_dir)
        embeddings = self.create_image_embeddings(image_paths)
        normalized_embeddings = self.normalize_embeddings(embeddings)
        metadata_list = self.make_metadata(image_paths)

        for index, (embedding, metadata) in enumerate(
            zip(normalized_embeddings, metadata_list)
        ):
            embedding_id = f"crop_{index}"

            self.save_embedding(
                id=embedding_id,
                embedding=embedding.tolist(),
                metadata=metadata,
            )
# crop embedding 완료 ------------------------------

