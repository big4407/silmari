from fastapi import APIRouter

from api.schemas.alert_schema import AlertRequest, AlertInfo
from core.llm.chain import run_alert_parse_chain
from services.sms_receiver import receive_alert

router = APIRouter()


@router.post("/parse", response_model=AlertInfo)
def parse_alert(req: AlertRequest):
    return run_alert_parse_chain(req.text)


@router.post("/receive")
async def receive_sms_alert(req: AlertRequest):
    return await receive_alert(req.text)
