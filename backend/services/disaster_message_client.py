"""행정안전부 재난문자 API HTTP 클라이언트 — MessageService.collect_messages 에서 사용."""
import httpx

from backend.core.config import settings


class DisasterMessageClient:
    async def fetch_messages(
        self,
        page_no: int = 1,
        num_of_rows: int = 10,
        crt_dt: str | None = None,
        rgn_nm: str | None = None,
    ) -> list[dict]:
        params = {
            "serviceKey": settings.DISASTER_API_SERVICE_KEY,
            "pageNo": page_no,
            "numOfRows": num_of_rows,
            "returnType": "json",
        }

        if crt_dt:
            params["crtDt"] = crt_dt

        if rgn_nm:
            params["rgnNm"] = rgn_nm

        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(
                settings.disaster_api_url,
                params=params,
            )
            response.raise_for_status()

        data = response.json()

        body = data.get("body")

        if isinstance(body, list):
            return body

        if isinstance(body, dict):
            items = body.get("items") or body.get("item") or []
            if isinstance(items, list):
                return items
            return [items]

        return []
