from pydantic import BaseModel
from typing import Optional


class AlertRequest(BaseModel):
    text: str


class AlertInfo(BaseModel):
    name: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    clothes: Optional[str] = None
    clothes_part: str = "upper"
    raw_text: str
