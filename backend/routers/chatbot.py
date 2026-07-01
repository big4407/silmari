from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.db.database import get_db
from backend.chatbot.schemas import ChatbotRequest, ChatbotResponse
from backend.services.chatbot_service import ChatbotService


router = APIRouter()


@router.post("/chat", response_model=ChatbotResponse)
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
