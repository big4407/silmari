from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.db.database import get_db
from backend.deps import get_current_user
from backend.db.models import User
from backend.schemas.chatbot_schema import ChatbotRequest, ChatbotResponse
from backend.services.chatbot_service import ChatbotService


router = APIRouter()


@router.post("/chat", response_model=ChatbotResponse)
def chat(
    request: ChatbotRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
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
