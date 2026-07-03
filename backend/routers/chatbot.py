from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.db.database import get_db
from backend.chatbot.schemas import ChatbotRequest, ChatbotResponse
from backend.services.chatbot_service import ChatbotService

from backend.deps import get_current_user
from backend.db.models import User

router = APIRouter()


@router.post("/chat", response_model=ChatbotResponse)
def chat(
    request: ChatbotRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = ChatbotService(db)

    result = service.chat(
        session_id=request.session_id,
        message=request.message,
        user_id=current_user.id,
    )

    return ChatbotResponse(
        response=result["response"],
        session_id=result["session_id"],
    )


@router.get("/session/{session_id}")
def get_chat_session(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = ChatbotService(db)
    return service.get_session_messages(user_id=current_user.id, session_id=session_id)
