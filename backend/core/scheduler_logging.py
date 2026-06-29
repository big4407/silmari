import logging
import os

# logs 폴더가 없으면 생성
os.makedirs("logs", exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    handlers=[
        logging.StreamHandler(),  # 콘솔 출력
        logging.FileHandler("logs/app.log", encoding="utf-8"),  # 파일 출력
    ],
)
