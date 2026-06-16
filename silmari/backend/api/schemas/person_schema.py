from pydantic import BaseModel
from typing import Optional


class PersonInfo(BaseModel):
    name: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    clothes: Optional[str] = None
    photo_url: Optional[str] = None
    missing_date: Optional[str] = None
    location: Optional[str] = None
