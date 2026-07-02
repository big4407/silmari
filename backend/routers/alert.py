"""
안내문자 파싱 API.

POST /parse   — 인상착의 구조화 (프론트·챗봇에서 미리보기용)
POST /receive — 외부 SMS 수신 연동 (sms_receiver)
"""
from fastapi import APIRouter

from backend.schemas.alert_schema import AlertRequest, AlertInfo
from backend.core.llm.chain import run_alert_parse_chain
from backend.services.sms_receiver import receive_alert

router = APIRouter()


@router.post("/parse", response_model=AlertInfo)
def parse_alert(req: AlertRequest):
    return run_alert_parse_chain(req.text)


@router.post("/receive")
async def receive_sms_alert(req: AlertRequest):
    return await receive_alert(req.text)
