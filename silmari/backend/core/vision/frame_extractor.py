import cv2
from typing import Generator, Tuple

import numpy as np


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
