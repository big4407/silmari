import cv2
from typing import Generator, Tuple
import numpy as np
import os
from pathlib import Path
from ultralytics import YOLO
from datetime import datetime
from backend.core.config import settings
from torchreid.utils import FeatureExtractor
import torch.nn.functional as F
import shutil
import json
from fashion_clip.fashion_clip import FashionCLIP
from backend.db.database import get_chromadb
from sqlalchemy.orm import Session
from backend.repositories.video_repository import VideoRepository
from backend.db.models import Video, VideoDetail

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
    # 만약 video_path = region_code/cctv_serial_no/recorded_at 이런 형식이라면 아닐경우 수정필요
    # "11680/CCTV001/20260706_103000.mp4"
    def process_videos(self, video_paths: list[str]):
        for video_path in video_paths:
            path = Path(video_path)
            video = Video(
                region_code = path.parts[-3],
                cctv_serial_no = path.parts[-2],
                recorded_at = datetime.strptime(path.stem, "%Y%m%d_%H%M%S"),
                file_path = str(path)
            )
            save_video = self.repository.create(video)
            embedding_id = f"video_{save_video.id}"
            self.repository.update_embedding_id(save_video, embedding_id)
            frames = self.frame_extract(video_path)
            details, crop_paths = self.person_detect(frames)
            self.save_embeddings_to_chroma(save_video.id, crop_paths, details)
            self.process_video_detail(save_video.id, details)

    def process_video_detail(self, video_id: int, details: list[dict]):
        for detail in details:
            video_detail = VideoDetail(
            video_id = video_id,
            video_timestamp = detail["video_timestamp"],
            crop_id = detail["crop_id"],
            position = detail["position"]
            )
            self.repository.create_detail(video_detail)

    def frame_extract(
            self, video_path:str, every_nth: int = 5
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
        saved_paths = []
        for idx, pos in enumerate(positions, 1):
            cap.set(cv2.CAP_PROP_POS_FRAMES, pos)

            ret, frame = cap.read()

            if ret:
                seconds = int(pos / fps)
                save_path = os.path.join(save_dir, f"{video_name}_frame_{seconds:05d}s.jpg")
                success = cv2.imwrite(save_path, frame)

                if success:
                    saved_count += 1
                    saved_paths.append(save_path)
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
        return saved_paths

    def person_detect(self, image_paths: list[str]):
        # 20260706_103000_frame_00010s <-이런형식의 프레임에서 초만 잘라낸다.
        "폴더 path를 주면 해당 폴더의 모든 frame에 대해 사람 식별함"
        details = []
        crop_paths = []
        image_paths = [Path(image_path) for image_path in image_paths]
        save_dir = Path("data/results/detected")

        save_dir.mkdir(parents=True, exist_ok=True)


        annotated_dir = Path("data/results/annotated_frames")
        annotated_dir.mkdir(parents=True, exist_ok=True)


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
                success = cv2.imwrite(str(save_path), person_crop)
                if success:
                    crop_paths.append(str(save_path))
                    details.append({
                        "video_timestamp":int(image_path.stem.split("_")[-1][:-1]),
                        "crop_id": person_idx,
                        "position": f"{x1}, {y1}, {x2}, {y2}"
                    })
        return details, crop_paths
        

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


# crop embedding ------------------------------------------------------
    def create_image_embeddings(self, crop_paths: list[str]):
        fclip = FashionCLIP("fashion-clip")
        path_strings = [str(path) for path in crop_paths]
        embeddings = fclip.encode_images(path_strings, batch_size=32)
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        return embeddings / norms
    def save_embeddings_to_chroma(self, video_id: int, crop_paths:list[str], details: list[dict]):
        collection = get_chromadb()
        embeddings = self.create_image_embeddings(crop_paths)
        for crop_path, embedding, detail in zip(crop_paths, embeddings, details):
            parts = Path(crop_path).stem.split("_")
                # 20260706_103000_frame_00010s_person_1.jpg
                # ["20260706", "103000", "frame", "00010s", "person", "1"]
            metadata = {
                "video_id": video_id,
                "image_path": str(crop_path),
                "video_timestamp":detail["video_timestamp"],
                "crop_id": detail["crop_id"],
                "position": detail["position"],
            }
            collection.upsert(
                ids=[f"video_{video_id}_timestamp_{metadata['video_timestamp']}_crop_{metadata['crop_id']}"],
                embeddings=[embedding.tolist()],
                metadatas=[metadata]
            )

    def get_embeddings_by_video_id(self, video_id: int):
        collection = get_chromadb()
        result = collection.get(
            where={"video_id": video_id},
            include=["embeddings", "metadatas"]
        )
        return result
    
    def search_embeddings(self, query: str, video_id: int, n_results: int = 5):
        fclip = FashionCLIP("fashion-clip")
        text_embeddings = fclip.encode_text([query], batch_size=1)
        text_embeddings = text_embeddings / np.linalg.norm(
            text_embeddings,
            axis=1,
            keepdims=True
            )
        collection = get_chromadb()
        result = collection.query(
            query_embeddings=text_embeddings.tolist(),
            n_results=n_results,
            where = {"video_id": video_id},
            )
        return result   #result["metadatas"][0]에  image_path가 있어 crop을 볼 수 있음.
# crop embedding 완료 -------------------------------------------------

    # def get_image_paths(image_dir):
    #     """
    #     동일인물 제거를한 unique_persons 폴더에서 jpg 이미지 경로 목록 반환
    #     """
    #     image_dir = Path(image_dir)
    #     image_paths = sorted(image_dir.glob("*.jpg"))
    #     return image_paths

    # def create_image_embeddings(image_paths):
    #     """
    #         이미지 경로 목록을 FashionCLIP 이미지 임베딩으로 변환
    #     """
    #     fclip = FashionCLIP("fashion-clip")
    #     path_strings = [str(path) for path in image_paths]
    #     embeddings = fclip.encode_images(path_strings, batch_size=32)
    #     return embeddings

    # def normalize_embeddings(embeddings):
    #     """
    #         코사인 유사도 계산용으로 정규화된 임베딩 반환:
    #     """
    #     norms = np.linalg.norm(
    #         embeddings,
    #         axis=1,
    #         keepdims=True
    #     )
    #     return embeddings / norms

    # def make_metadata(image_paths):
    #     """
    #         index, group_id, image_path 목록 생성
    #     """
    #     metadata = []
    #     for index, image_path in enumerate(image_paths):
    #         metadata.append({
    #             "index": index,
    #             "image_path": str(image_path)
    #             # "crop_id"
    #             # embedding,
    #             # video_id,
    #             # frame_number,
    #             # timestamp,
    #             # location,
    #             # person_index
    #         })
    #     return metadata

    

# # ──────────────────────────────────────────────────────────────────────────
# # DB 접근 함수
# # crop_embedding / 
# # ──────────────────────────────────────────────────────────────────────────
#     def save_embedding(id, embedding, metadata):
#         collection = get_chromadb()
#         collection.upsert(
#             ids=[id],
#             embeddings=[embedding],
#             metadatas=[metadata]
#         )


#     def crop_embedding(self, image_dir):
#         image_paths = self.get_image_paths(image_dir)
#         embeddings = self.create_image_embeddings(image_paths)
#         normalized_embeddings = self.normalize_embeddings(embeddings)
#         metadata_list = self.make_metadata(image_paths)

#         for index, (embedding, metadata) in enumerate(
#             zip(normalized_embeddings, metadata_list)
#         ):
#             embedding_id = f"crop_{index}"

#             self.save_embedding(
#                 id=embedding_id,
#                 embedding=embedding.tolist(),
#                 metadata=metadata,
#             )

