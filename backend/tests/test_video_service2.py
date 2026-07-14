"""VideoService 단위 테스트.

이 파이프라인은 YOLO·FashionCLIP·OpenCV·실제 영상에 의존하므로,
무거운 외부 의존성(모델 로드·영상 디코딩·Chroma)은 모두 mock 으로 대체하고
서비스의 '로직'만 검증한다:

  - process_videos: 경로 파싱(region/날짜/cctv) → VideoCreate → DB 저장 흐름
  - person_detect: YOLO 결과 → crop 저장 → details(video_timestamp/crop_id/position)
  - save_embeddings_to_chroma: Chroma upsert 시 id/metadata 구성
  - frame_extract: 열기 실패 시 예외

실제 모델로 도는 통합 테스트는 test_video_pipeline_integration.py 참고(환경 필요).
"""

import sys
import types
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest


# ──────────────────────────────────────────────────────────────────────────
# 무거운 외부 의존성 모듈을 import 전에 가짜로 등록
# (video_service 는 모듈 로드 시 YOLO()·FashionCLIP() 을 즉시 생성하므로)
# ──────────────────────────────────────────────────────────────────────────
def _install_fake_modules():
    # ultralytics.YOLO
    ultra = types.ModuleType("ultralytics")
    ultra.YOLO = MagicMock(return_value=MagicMock(name="yolo_model"))
    sys.modules["ultralytics"] = ultra

    # fashion_clip.fashion_clip.FashionCLIP
    fc_pkg = types.ModuleType("fashion_clip")
    fc_mod = types.ModuleType("fashion_clip.fashion_clip")
    fc_mod.FashionCLIP = MagicMock(return_value=MagicMock(name="fclip"))
    fc_pkg.fashion_clip = fc_mod
    sys.modules["fashion_clip"] = fc_pkg
    sys.modules["fashion_clip.fashion_clip"] = fc_mod

    # torchreid.utils.FeatureExtractor
    tr_pkg = types.ModuleType("torchreid")
    tr_utils = types.ModuleType("torchreid.utils")
    tr_utils.FeatureExtractor = MagicMock()
    tr_pkg.utils = tr_utils
    sys.modules["torchreid"] = tr_pkg
    sys.modules["torchreid.utils"] = tr_utils

    # torch.nn.functional
    torch_mod = types.ModuleType("torch")
    torch_nn = types.ModuleType("torch.nn")
    torch_F = types.ModuleType("torch.nn.functional")
    torch_nn.functional = torch_F
    torch_mod.nn = torch_nn
    sys.modules["torch"] = torch_mod
    sys.modules["torch.nn"] = torch_nn
    sys.modules["torch.nn.functional"] = torch_F

    # cv2
    sys.modules["cv2"] = MagicMock(name="cv2")


_install_fake_modules()


# ──────────────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────────────
@pytest.fixture
def service():
    """VideoService 인스턴스 — repository 를 mock 으로 대체."""
    from backend.services.video_service import VideoService

    db = MagicMock(name="db_session")
    svc = VideoService(db)
    svc.repository = MagicMock(name="repository")
    # create 는 id 가 매겨진 Video 를 돌려주도록
    created = MagicMock()
    created.id = 3
    svc.repository.create.return_value = created
    return svc


# ──────────────────────────────────────────────────────────────────────────
# process_videos — 경로 파싱 & 저장 흐름
# ──────────────────────────────────────────────────────────────────────────
class TestProcessVideos:
    def test_경로_파싱_결과가_VideoCreate로_저장된다(self, service):
        """region/날짜/cctv 를 경로에서 뽑아 Video 를 만든다."""
        video_path = "11680/20260701/CCTV001/video1.mp4"

        # 파이프라인 내부 무거운 단계는 patch
        with (
            patch.object(service, "frame_extract", return_value=["f1.jpg"]),
            patch.object(service, "person_detect", return_value=([], [])),
            patch.object(service, "save_embeddings_to_chroma"),
            patch.object(service, "process_video_detail"),
        ):
            service.process_videos([video_path])

        # repository.create 가 Video 로 호출됐는지
        assert service.repository.create.called
        saved_video = service.repository.create.call_args.args[0]
        assert saved_video.region_code == "11680"
        assert saved_video.cctv_serial_no == "CCTV001"
        assert saved_video.recorded_at == date(2026, 7, 1)  # 날짜만(시각 없음)
        assert saved_video.file_path == video_path

    def test_여러_영상을_순서대로_처리한다(self, service):
        paths = [
            "11680/20260701/CCTV001/a.mp4",
            "11680/20260702/CCTV002/b.mp4",
        ]
        with (
            patch.object(service, "frame_extract", return_value=[]),
            patch.object(service, "person_detect", return_value=([], [])),
            patch.object(service, "save_embeddings_to_chroma"),
            patch.object(service, "process_video_detail"),
        ):
            service.process_videos(paths)

        assert service.repository.create.call_count == 2


# ──────────────────────────────────────────────────────────────────────────
# process_video_detail — details → VideoDetail 저장
# ──────────────────────────────────────────────────────────────────────────
class TestProcessVideoDetail:
    def test_각_detail이_create_detail로_저장된다(self, service):
        details = [
            {"video_timestamp": 10, "crop_id": 1, "position": "1, 2, 3, 4"},
            {"video_timestamp": 15, "crop_id": 2, "position": "5, 6, 7, 8"},
        ]
        service.process_video_detail(video_id=3, details=details)
        assert service.repository.create_detail.call_count == 2


# ──────────────────────────────────────────────────────────────────────────
# frame_extract — 열기 실패 시 예외 (exit() 대신)
# ──────────────────────────────────────────────────────────────────────────
class TestFrameExtract:
    def test_영상_열기_실패시_RuntimeError(self, service):
        import backend.services.video_service as vs

        fake_cap = MagicMock()
        fake_cap.isOpened.return_value = False
        with patch.object(vs.cv2, "VideoCapture", return_value=fake_cap):
            with pytest.raises(RuntimeError, match="영상을 열지 못했습니다"):
                service.frame_extract("nonexistent.mp4")


# ──────────────────────────────────────────────────────────────────────────
# person_detect — YOLO 결과 → details 구성
# ──────────────────────────────────────────────────────────────────────────
class TestPersonDetect:
    def test_탐지된_박스가_details로_변환된다(self, service):
        import backend.services.video_service as vs

        # YOLO 결과 mock: 박스 1개 (좌표 10,20,30,40)
        # 코드가 box.xyxy[0].cpu().numpy().astype(int) 로 접근하므로 체인을 맞춘다.
        xyxy0 = MagicMock()
        xyxy0.cpu.return_value.numpy.return_value = np.array([10, 20, 30, 40])
        fake_box = MagicMock()
        fake_box.xyxy = [xyxy0]
        conf0 = MagicMock()
        conf0.cpu.return_value.item.return_value = 0.9
        fake_box.conf = [conf0]
        fake_result = MagicMock()
        fake_result.boxes = [fake_box]

        frame_path = "data/results/frames/video1_frame_00010s.jpg"

        with (
            patch.object(vs.model, "predict", return_value=[fake_result]),
            patch.object(
                vs.cv2, "imread", return_value=np.zeros((100, 100, 3), dtype=np.uint8)
            ),
            patch.object(vs.cv2, "imwrite", return_value=True),
            patch("pathlib.Path.mkdir"),
        ):
            details, crop_paths = service.person_detect([frame_path])

        assert len(details) == 1
        d = details[0]
        assert d["video_timestamp"] == 10  # 파일명 _00010s → 10초
        assert d["crop_id"] == 1
        assert d["position"] == "10, 20, 30, 40"
        assert len(crop_paths) == 1


# ──────────────────────────────────────────────────────────────────────────
# save_embeddings_to_chroma — Chroma id/metadata 구성 (video.id 기반)
# ──────────────────────────────────────────────────────────────────────────
class TestSaveEmbeddingsToChroma:
    def test_chroma_id는_video_id로_구성된다(self, service):
        import backend.services.video_service as vs

        fake_collection = MagicMock()
        crop_paths = ["c1.jpg"]
        details = [{"video_timestamp": 10, "crop_id": 1, "position": "1, 2, 3, 4"}]

        with (
            patch.object(vs, "get_chromadb", return_value=fake_collection),
            patch.object(
                service,
                "create_image_embeddings",
                return_value=np.array([[0.1, 0.2, 0.3]]),
            ),
        ):
            service.save_embeddings_to_chroma(
                video_id=3, crop_paths=crop_paths, details=details
            )

        assert fake_collection.upsert.called
        kwargs = fake_collection.upsert.call_args.kwargs
        # id 가 video_{id}_timestamp_{ts}_crop_{crop} 형식
        assert kwargs["ids"] == ["video_3_timestamp_10_crop_1"]
        # metadata 에 video_id 가 들어있음 (embedding_id 불필요)
        assert kwargs["metadatas"][0]["video_id"] == 3
        assert kwargs["metadatas"][0]["crop_id"] == 1


# ──────────────────────────────────────────────────────────────────────────
# get/search — Chroma 조회가 video_id 필터로 나가는지
# ──────────────────────────────────────────────────────────────────────────
class TestChromaQuery:
    def test_get_embeddings_by_video_id_필터(self, service):
        import backend.services.video_service as vs

        fake_collection = MagicMock()
        with patch.object(vs, "get_chromadb", return_value=fake_collection):
            service.get_embeddings_by_video_id(3)
        assert fake_collection.get.call_args.kwargs["where"] == {"video_id": 3}

    def test_search_embeddings_필터(self, service):
        import backend.services.video_service as vs

        fake_collection = MagicMock()
        vs._fclip.encode_text = MagicMock(return_value=np.array([[0.1, 0.2, 0.3]]))
        with patch.object(vs, "get_chromadb", return_value=fake_collection):
            service.search_embeddings("빨간 옷", video_id=3, n_results=5)
        kwargs = fake_collection.query.call_args.kwargs
        assert kwargs["where"] == {"video_id": 3}
        assert kwargs["n_results"] == 5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
