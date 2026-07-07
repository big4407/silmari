"""
실종자 정보 외부 API 연동 (safe182.go.kr).

fetch_missing_persons — 실종자 목록 (result.py /list)
receive_alert         — SMS 수신 시 파이프라인 트리거 (향후)
"""
import httpx
from typing import Optional

from backend.core.config import settings

BASE_URL = "https://www.safe182.go.kr/api/lcm/findChildList.do"


async def fetch_missing_persons(
    name: Optional[str] = None, age: Optional[int] = None
) -> list:
    params = {
        "esntlId": settings.SAFE182_ESNTL_ID,
        "authKey": settings.SAFE182_API_KEY,
        "rowSize": 50,
        "page": 1,
    }
    if name:
        params["nm"] = name
    if age:
        params["age1"] = str(age)
        params["age2"] = str(age)

    try:
        async with httpx.AsyncClient() as client:
            res = await client.post(BASE_URL, data=params, timeout=5)
            data = res.json()
            persons = data.get("list", [])

            return [
                {
                    "name": p.get("nm"),
                    "age": p.get("ageNow"),
                    "gender": p.get("sexdstnDscd"),
                    "clothes": p.get("alldressingDscd"),
                    "photo_url": p.get("tknphotograph"),
                    "missing_date": p.get("occrde"),
                    "location": p.get("occrAdres"),
                }
                for p in persons
            ]
    except Exception as e:
        print(f"safe182 API 오류: {e}")
        return []


def fetch_missing_persons_dummy() -> list:
    return [
        {
            "name": "홍길동",
            "age": 65,
            "gender": "남",
            "clothes": "검은 점퍼, 파란 바지",
            "photo_url": None,
            "missing_date": "2024-06-09",
            "location": "서울 종로구",
        },
        {
            "name": "김영희",
            "age": 72,
            "gender": "여",
            "clothes": "베이지 코트, 검은 바지",
            "photo_url": None,
            "missing_date": "2024-06-10",
            "location": "부산 해운대구",
        },
    ]


async def receive_alert(text: str) -> dict:
    """안전안내문자 수신 처리 (추후 Webhook/SMS 연동)"""
    from backend.core.llm.chain import run_alert_parse_chain

    return run_alert_parse_chain(text).model_dump()
