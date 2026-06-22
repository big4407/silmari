import os
import cv2
from pathlib import Path
cap = cv2.VideoCapture('data/CCTV/lo_e1281_c1.mp4')
video_path = Path("data/CCTV/lo_e1281_c1.mp4")
video_name = video_path.stem

if not cap.isOpened():
    print("오류: 영상을 열지 못했습니다.")
    exit()

save_dir = "data/results/frames"
os.makedirs(save_dir, exist_ok=True)

fps = cap.get(cv2.CAP_PROP_FPS)
width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
total_frame = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

print(fps, width, height, total_frame)

positions = [
    i * int(fps)
    for i in range(int(total_frame / fps))
    if i % 5 == 0
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

cap.release()

print(f"저장된 프레임 수: {saved_count}")