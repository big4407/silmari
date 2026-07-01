from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.db.database import get_db
from backend.chatbot.schemas import ChatbotRequest, ChatbotResponse
from backend.services.chatbot_service import ChatbotService


router = APIRouter(prefix="/chatbot", tags=["Chatbot"])


@router.post("/chat", response_model=ChatbotResponse)
def chat(
    request: ChatbotRequest,
    db: Session = Depends(get_db),
):
    service = ChatbotService(db)

    result = service.chat(
        user_id=request.user_id,
        message=request.message,
        prev_state=request.state,
    )

    response = result["response"]
    state = result.copy()
    state.pop("response", None)

    return ChatbotResponse(
        response=response,
        state=state,
    )
