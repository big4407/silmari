import cv2
import numpy as np
import os
from pathlib import Path
from ultralytics import YOLO
from datetime import date, datetime, timedelta
from backend.core.config import settings
from torchreid.utils import FeatureExtractor
import torch.nn.functional as F
import shutil
import json
from fashion_clip.fashion_clip import FashionCLIP
from backend.db.database import get_chromadb
from sqlalchemy.orm import Session
from backend.repositories.video_repository import VideoRepository
from backend.schemas.video_schema import VideoCreate, VideoDetailCreate
from backend.db.models import Video, VideoDetail

_model = None
_fclip = None


def _get_yolo_model() -> YOLO:
    global _model
    if _model is None:
        model_path = Path(settings.yolo_model_path)
        _model = YOLO(str(model_path) if model_path.exists() else "yolov8n.pt")
    return _model


def _get_fashion_clip() -> FashionCLIP:
    # FashionCLIP 은 로드가 매우 무거우므로(수 초~수십 초) 최초 사용 시 1회만 생성해 재사용한다.
    global _fclip
    if _fclip is None:
        _fclip = FashionCLIP("fashion-clip")
    return _fclip

# 처리 대상 영상 확장자
_VIDEO_EXTENSIONS = {".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm"}


class VideoService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = VideoRepository(db)

    # ──────────────────────────────────────────────────────────────────────────
    # 기능 함수
    # frame_extract /
    # ──────────────────────────────────────────────────────────────────────────
    # video_path = region_code/YYYYMMDD/cctv_serial_no/
    # "11680/20260701/CCTV001/video1.mp4"
    def collect_video_paths(self, start_date: date, end_date: date) -> list[str]:
        """지정한 날짜 범위(양끝 포함)의 CCTV 영상 경로를 수집한다.

        경로 규칙: {cctv_data_dir}/{region_code}/{YYYYMMDD}/{cctv_serial_no}/*.mp4
        start_date 부터 end_date 까지 하루씩 순회하며, 각 날짜 폴더의
        모든 region·cctv 하위 영상을 모은다.
        """
        base_dir = Path(settings.cctv_data_dir)
        if not base_dir.exists():
            return []

        video_paths: list[str] = []
        current = start_date
        while current <= end_date:
            day_str = current.strftime("%Y%m%d")
            for region_dir in base_dir.iterdir():
                if not region_dir.is_dir():
                    continue
                day_dir = region_dir / day_str
                if not day_dir.is_dir():
                    continue
                for file in day_dir.rglob("*"):
                    if file.suffix.lower() in _VIDEO_EXTENSIONS:
                        video_paths.append(str(file.resolve()))
            current += timedelta(days=1)

        return video_paths

    def process_videos(self, video_paths: list[str]) -> dict:
        """영상 목록을 처리해 Video/VideoDetail 및 Chroma 에 저장.

        같은 file_path 가 이미 처리되어 있으면 건너뛴다(중복 방지).
        영상 하나가 실패해도(깨진 파일, 너무 짧은 영상 등) 나머지는 계속
        처리한다 — 한 영상 때문에 배치 전체가 멈추지 않게.
        반환: {"processed": 처리 건수, "skipped": 중복 건수, "failed": 실패 건수}
        """
        processed = 0
        skipped = 0
        failed = 0
        for video_path in video_paths:
            path = Path(video_path)
            file_path = str(path)

            # 중복 방지 — 이미 처리한 경로면 건너뜀
            if self.repository.exists_by_file_path(file_path):
                skipped += 1
                continue

            try:
                video = VideoCreate(
                    region_code=path.parts[-4],
                    cctv_serial_no=path.parts[-2],
                    recorded_at=datetime.strptime(path.parts[-3], "%Y%m%d").date(),
                    file_path=file_path,
                )
                save_video = self.repository.create(Video(**video.model_dump()))
                frames = self.frame_extract(video_path)
                details, crop_paths = self.person_detect(frames)
                self.save_embeddings_to_chroma(save_video.id, crop_paths, details)
                self.process_video_detail(save_video.id, details)
                processed += 1
            except Exception as exc:
                failed += 1
                print(f"[영상 처리 실패] {video_path}: {exc}")
                continue

        return {"processed": processed, "skipped": skipped, "failed": failed}

    def process_video_detail(self, video_id: int, details: list[dict]):
        for detail in details:
            video_detail = VideoDetailCreate(
                video_id=video_id,
                video_timestamp=detail["video_timestamp"],
                crop_id=detail["crop_id"],
                position=detail["position"],
            )
            self.repository.create_detail(VideoDetail(**video_detail.model_dump()))

    def frame_extract(self, video_path: str, every_nth: int = 5):
        cap = cv2.VideoCapture(video_path)
        path = Path(video_path)
        video_name = path.stem

        if not cap.isOpened():
            raise RuntimeError(f"영상을 열지 못했습니다: {video_path}")

        save_dir = Path("data/results/frames")
        save_dir.mkdir(parents=True, exist_ok=True)

        fps = cap.get(cv2.CAP_PROP_FPS)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total_frame = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        # print(fps, width, height, total_frame)

        positions = [
            i * int(fps) for i in range(int(total_frame / fps)) if i % every_nth == 0
        ]

        saved_count = 0
        saved_paths = []
        for idx, pos in enumerate(positions, 1):
            cap.set(cv2.CAP_PROP_POS_FRAMES, pos)

            ret, frame = cap.read()

            if ret:
                seconds = int(pos / fps)
                save_path = os.path.join(
                    save_dir, f"{video_name}_frame_{seconds:05d}s.jpg"
                )
                success = cv2.imwrite(save_path, frame)

                if success:
                    saved_count += 1
                    saved_paths.append(save_path)
                else:
                    print(f"저장 실패: {save_path}")

        cap.release()
        # print(f"저장된 프레임 수: {saved_count}")
        return saved_paths

    def person_detect(self, image_paths: list[str]):
        # 20260706_103000_frame_00010s <-이런형식의 프레임에서 초만 잘라낸다.
        "폴더 path를 주면 해당 폴더의 모든 frame에 대해 사람 식별함"
        details = []
        crop_paths = []
        image_paths = [Path(image_path) for image_path in image_paths]

        if not image_paths:
            # 영상이 너무 짧거나(예: 5초 미만) 깨져서 frame_extract가 프레임을
            # 하나도 못 뽑은 경우 — YOLO에 빈 리스트를 넘기면 predict()가 빈
            # 결과를 돌려주고 results[0]에서 IndexError가 난다. 조용히 건너뛴다.
            print("[person_detect] 추출된 프레임이 없어 건너뜁니다.")
            return details, crop_paths

        save_dir = Path("data/results/detected")

        save_dir.mkdir(parents=True, exist_ok=True)

        annotated_dir = Path("data/results/annotated_frames")
        annotated_dir.mkdir(parents=True, exist_ok=True)

        image_paths = sorted(image_paths)

        results = _get_yolo_model().predict(
            source=image_paths, conf=0.4, save=False, classes=0
        )
        # print(results[0])

        for image_path, r in zip(image_paths, results):
            frame = cv2.imread(str(image_path))
            if frame is None:
                continue
            for person_idx, box in enumerate(r.boxes, 1):
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy().astype(int)

                person_crop = frame[y1:y2, x1:x2]
                save_path = save_dir / f"{image_path.stem}_person_{person_idx}.jpg"
                success = cv2.imwrite(str(save_path), person_crop)
                if success:
                    crop_paths.append(str(save_path))
                    details.append(
                        {
                            "video_timestamp": int(image_path.stem.split("_")[-1][:-1]),
                            "crop_id": person_idx,
                            "position": f"{x1}, {y1}, {x2}, {y2}",
                        }
                    )
        return details, crop_paths

    def check_same_person(self, detected_path: str):
        image_dir = Path(detected_path)
        save_dir = Path("data/results/unique_persons")
        save_dir.mkdir(parents=True, exist_ok=True)
        json_path = save_dir / "group_data.json"
        extractor = FeatureExtractor(model_name="osnet_x1_0", device="cpu")

        image_paths = []
        for ext in ["*.jpg"]:
            image_paths.extend(image_dir.glob(ext))
        image_paths = sorted(image_paths)

        if not image_paths:
            raise ValueError(f"사람 crop 이미지가 없습니다: {detected_path}")

        features = extractor([str(path) for path in image_paths])

        groups = [{"representative_index": 0, "members": [0]}]

        for i in range(1, len(features)):
            best_group = None
            best_similarity = -1
            for group in groups:
                representative_index = group["representative_index"]

                similarity = F.cosine_similarity(
                    features[i].unsqueeze(0),
                    features[representative_index].unsqueeze(0),
                ).item()
                if similarity > best_similarity:
                    best_similarity = similarity
                    best_group = group

            if best_similarity >= 0.7:
                best_group["members"].append(i)
            else:
                groups.append({"representative_index": i, "members": [i]})

        group_data = {}
        for group_number, group in enumerate(groups, start=1):
            representative_index = group["representative_index"]
            source_path = image_paths[representative_index]
            save_path = (
                save_dir
                / f"group_{group_number:04d}{source_path.stem}{source_path.suffix}"
            )
            shutil.copy2(source_path, save_path)
            group_data[f"group_{group_number:04d}"] = {
                "representative": str(save_path),
                "members": [str(image_paths[index]) for index in group["members"]],
            }

        with open(json_path, "w", encoding="utf-8") as file:
            json.dump(group_data, file, ensure_ascii=False, indent=4)

    # crop embedding ------------------------------------------------------
    def create_image_embeddings(self, crop_paths: list[str]):
        path_strings = [str(path) for path in crop_paths]
        embeddings = _get_fashion_clip().encode_images(path_strings, batch_size=32)
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        return embeddings / norms

    def save_embeddings_to_chroma(
        self, video_id: int, crop_paths: list[str], details: list[dict]
    ):
        collection = get_chromadb()
        embeddings = self.create_image_embeddings(crop_paths)
        for crop_path, embedding, detail in zip(crop_paths, embeddings, details):
            # 20260706_103000_frame_00010s_person_1.jpg
            # ["20260706", "103000", "frame", "00010s", "person", "1"]
            metadata = {
                "video_id": video_id,
                "image_path": str(crop_path),
                "video_timestamp": detail["video_timestamp"],
                "crop_id": detail["crop_id"],
                "position": detail["position"],
            }
            collection.upsert(
                ids=[
                    f"video_{video_id}_timestamp_{metadata['video_timestamp']}_crop_{metadata['crop_id']}"
                ],
                embeddings=[embedding.tolist()],
                metadatas=[metadata],
            )

    def get_embeddings_by_video_id(self, video_id: int):
        collection = get_chromadb()
        result = collection.get(
            where={"video_id": video_id}, include=["embeddings", "metadatas"]
        )
        return result

    def search_embeddings(self, query: str, video_id: int, n_results: int = 5):
        text_embeddings = _get_fashion_clip().encode_text([query], batch_size=1)
        text_embeddings = text_embeddings / np.linalg.norm(
            text_embeddings, axis=1, keepdims=True
        )
        collection = get_chromadb()
        result = collection.query(
            query_embeddings=text_embeddings.tolist(),
            n_results=n_results,
            where={"video_id": video_id},
        )
        return result  # result["metadatas"][0]에  image_path가 있어 crop을 볼 수 있음.

    def search_embeddings_multi(
        self, query: str, video_ids: list[int] | None = None, n_results: int = 20
    ):
        """여러 영상(video_ids)의 임베딩 안에서 텍스트 유사도로 검색한다.

        video_ids가 None이면 전체 컬렉션에서 검색한다(지역·기간 필터 없이 전수 검색).
        하나의 챗봇/검색 요청은 보통 지역·기간으로 video_ids를 먼저 좁혀서 넘긴다.
        """
        text_embeddings = _get_fashion_clip().encode_text([query], batch_size=1)
        text_embeddings = text_embeddings / np.linalg.norm(
            text_embeddings, axis=1, keepdims=True
        )
        collection = get_chromadb()
        kwargs = {
            "query_embeddings": text_embeddings.tolist(),
            "n_results": n_results,
        }
        if video_ids:
            kwargs["where"] = {"video_id": {"$in": video_ids}}
        return collection.query(**kwargs)