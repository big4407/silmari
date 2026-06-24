import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BASE_DIR.parent

API_KEY = os.getenv("SAFE182_API_KEY")
ESNTL_ID = os.getenv("SAFE182_ESNTL_ID")
SAFETYDATA_SERVICE_KEY = os.getenv("SAFETYDATA_SERVICE_KEY") or os.getenv("YOUR_API_KEY")
_raw_api_url = os.getenv(
    "SAFETYDATA_API_URL",
    "https://www.safetydata.go.kr/V2/api/DSSP-IF-00247",
)
if _raw_api_url and "?" in _raw_api_url:
    _raw_api_url = _raw_api_url.split("?")[0]
if _raw_api_url and not _raw_api_url.startswith("http"):
    _raw_api_url = f"https://www.safetydata.go.kr{_raw_api_url}"
SAFETYDATA_API_URL = _raw_api_url
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./silmari.db")
UPLOAD_DIR = os.getenv("UPLOAD_DIR", str(PROJECT_ROOT / "data" / "uploads"))
YOLO_MODEL_PATH = os.getenv("YOLO_MODEL_PATH", str(PROJECT_ROOT / "models" / "yolo" / "yolov8n.pt"))
CCTV_DATA_DIR = os.getenv("CCTV_DATA_DIR", str(PROJECT_ROOT / "data" / "CCTV"))
RESULTS_DIR = os.getenv("RESULTS_DIR", str(PROJECT_ROOT / "data" / "results"))
