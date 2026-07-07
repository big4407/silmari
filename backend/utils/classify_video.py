from pathlib import Path
import random
import shutil

base_dir = Path(__file__).resolve().parents[2]
cctv_dir = base_dir / "data" / "CCTV"
source_dir = cctv_dir / "unclassified"
video_paths = list(source_dir.glob("*.mp4"))

dong_dirs = [
    path 
    for path in cctv_dir.iterdir()
    if path.is_dir() and path.name != "unclassified"
]
for video_path in video_paths:
    target_dir = random.choice(dong_dirs)
    shutil.move(video_path, target_dir / video_path.name)
    print(target_dir)
