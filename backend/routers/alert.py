"""
[화면] DevAlertPage
[서비스] llm.chain.run_alert_parse_chain · sms_receiver.receive_alert
[테이블] 없음 (parse) · 수신 연동(receive)
"""
from fastapi import APIRouter

from backend.schemas.alert_schema import AlertRequest, AlertInfo
from backend.core.llm.chain import run_alert_parse_chain
from backend.services.sms_receiver import receive_alert

router = APIRouter()


@router.post(
    "/parse",
    response_model=AlertInfo,
    summary="안내문자 인상착의 파싱",
    description="안내문자 텍스트를 LLM으로 구조화 JSON(이름·나이·옷차림 등)으로 변환합니다.",
    include_in_schema=False,
)
def parse_alert(req: AlertRequest):
    return run_alert_parse_chain(req.text)


@router.post("/receive", include_in_schema=False)
async def receive_sms_alert(req: AlertRequest):
    return await receive_alert(req.text)
