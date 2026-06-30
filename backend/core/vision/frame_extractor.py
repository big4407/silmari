"""
CCTV 영상 → 프레임 시퀀스 추출.

[런타임] extract_frames() — 파이프라인에서 사용 (every_nth=5, 약 6fps 샘플링)
[오프라인] frame_extract() — 디스크에 JPG 저장 (개발·디버깅용)
"""
import cv2
from typing import Generator, Tuple

import numpy as np

import os
from pathlib import Path


def extract_frames(
    video_path: str, every_nth: int = 5
) -> Generator[Tuple[int, np.ndarray, float], None, None]:
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    frame_idx = 0

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        if frame_idx % every_nth == 0:
            yield frame_idx, frame, frame_idx / fps
        frame_idx += 1

    cap.release()

def frame_extract(
        video_path:str, every_nth: int = 5
):
    cap = cv2.VideoCapture(video_path)
    path = Path(video_path)
    video_name = path.stem

    if not cap.isOpened():
        print("오류: 영상을 열지 못했습니다.")
        exit()
    if not cap.isOpened():
        print("오류: 영상을 열지 못했습니다.")
        exit()

    save_dir = Path("data/results/frames")
    save_dir.mkdir(parents=True, exist_ok=True)
    save_dir = Path("data/results/frames")
    save_dir.mkdir(parents=True, exist_ok=True)

    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frame = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frame = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    print(fps, width, height, total_frame)
    print(fps, width, height, total_frame)

    positions = [
        i * int(fps)
        for i in range(int(total_frame / fps))
        if i % every_nth == 0
    ]

    saved_count = 0
    saved_count = 0

    for idx, pos in enumerate(positions, 1):
        cap.set(cv2.CAP_PROP_POS_FRAMES, pos)
    for idx, pos in enumerate(positions, 1):
        cap.set(cv2.CAP_PROP_POS_FRAMES, pos)

        ret, frame = cap.read()
        ret, frame = cap.read()

        if ret:
            seconds = int(pos / fps)
            save_path = os.path.join(save_dir, f"{video_name}_frame_{seconds:05d}s.jpg")
            success = cv2.imwrite(save_path, frame)
        if ret:
            seconds = int(pos / fps)
            save_path = os.path.join(save_dir, f"{video_name}_frame_{seconds:05d}s.jpg")
            success = cv2.imwrite(save_path, frame)

            if success:
                saved_count += 1
            else:
                print(f"저장 실패: {save_path}")
            if success:
                saved_count += 1
            else:
                print(f"저장 실패: {save_path}")

    cap.release()
    cap.release()

    print(f"저장된 프레임 수: {saved_count}")
    
if __name__ == "__main__":
    frame_extract("data\CCTV\output_video_1_1_1.mp4")