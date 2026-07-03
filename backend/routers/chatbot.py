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
    """ 
    챗봇을 직접 호출하는데 사용하는 함수. 사용자 요청(채팅 등)과 사용자 정보를 받아서 챗봇의 응답을 받아온다.
    """
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
    """
    챗봇과의 채팅 세션을 읽어오는 함수. session_id와 사용자 정보를 이용하여 채팅 세션을 읽어온다.
    """
    service = ChatbotService(db)
    return service.get_session_messages(user_id=current_user.id, session_id=session_id)
