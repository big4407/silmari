from pydantic import BaseModel
from typing import List, Optional

from api.schemas.alert_schema import AlertInfo


class DetectionItem(BaseModel):
    frame: int
    confidence: float
    timestamp_sec: float
    color_ratio: float = 0.0
    face_similarity: float = 0.0
    image_base64: str
    bbox: List[int] = []


class AnalysisResult(BaseModel):
    sms_info: AlertInfo
    total_detections: int
    face_recognition_used: bool
    detections: List[DetectionItem]
