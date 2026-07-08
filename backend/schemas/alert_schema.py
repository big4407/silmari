"""
안내문자 파싱 요청/응답 Pydantic 스키마.

AlertInfo — pipeline·matcher 가 사용하는 인상착의 구조화 결과
"""
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
