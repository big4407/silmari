"""
[화면] ChatbotPage.jsx, DevChatbotPage
[서비스] chatbot_service.ChatbotService → LangGraph
[테이블] chatbot_session
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.db.database import get_db
from backend.chatbot.schemas import ChatbotRequest, ChatbotResponse
from backend.services.chatbot_service import ChatbotService


router = APIRouter()


@router.post(
    "/chat",
    response_model=ChatbotResponse,
    summary="챗봇 대화",
    description="세션 ID 기반 대화형 실종자 검색·안내문자 파싱.",
)
def chat(
    request: ChatbotRequest,
    db: Session = Depends(get_db),
):
    service = ChatbotService(db)

    result = service.chat(
        session_id=request.session_id,
        message=request.message,
    )

    return ChatbotResponse(
        response=result["response"],
        session_id=result["session_id"],
    )
