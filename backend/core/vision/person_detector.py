from ultralytics import YOLO
from pathlib import Path
import cv2
model = YOLO("yolov8n.pt")
image_dir = Path("data/results/frames")
save_dir = Path("data/results/detected")

save_dir.mkdir(parents=True, exist_ok=True)
image_paths = []

for ext in ["*.jpg"]:
    image_paths.extend(image_dir.glob(ext))

image_paths = sorted(image_paths)

results = model.predict(source=image_paths, conf=0.1, save=False, classes=0)
print(results[0])

for image_path, r in zip(image_paths, results):
    frame = cv2.imread(str(image_path))
    if frame is None:
        continue
    for person_idx, box in enumerate(r.boxes, 1):
        x1, y1, x2, y2 = box.xyxy[0].cpu().numpy().astype(int)

        person_crop = frame[y1:y2, x1:x2]
        
        save_path = save_dir / f"{image_path.stem}_person_{person_idx}.jpg"
        cv2.imwrite(str(save_path), person_crop)

        print(x1, y1, x2, y2)