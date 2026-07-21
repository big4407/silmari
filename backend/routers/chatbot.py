from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from backend.db.database import get_db
from backend.deps import get_current_user
from backend.db.models import User
from backend.schemas.chatbot_schema import ChatbotRequest, ChatbotResponse
from backend.services.chatbot_service import ChatbotService

import uuid

router = APIRouter()


@router.post("/chat", response_model=ChatbotResponse)
def chat(
    request: ChatbotRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    챗봇을 직접 호출하는데 사용하는 함수. 사용자 요청(채팅 등)과 사용자 정보를 받아서 챗봇의 응답을 받아온다.
    """
    service = ChatbotService(db)

    result = service.chat(
        session_id=request.session_id,
        message=request.message,
        user_id=current_user.id,
        user_role=current_user.role.value if current_user.role else None,
    )

    return ChatbotResponse(
        response=result["response"],
        session_id=result["session_id"],
        search_id=result.get("search_id"),
        search_inserted=result.get("search_inserted", False),
        offer_case_registration=result.get("offer_case_registration", False),
        case_prefill=result.get("case_prefill"),
    )


@router.get("/session")
def create_chat_session(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    유저가 세션을 가지고 있지 않은 경우, 새로운 챗봇 세션을 생성하고, message를 반환한다.
    """
    service = ChatbotService(db)

    user_session = service.get_session_by_user_id(current_user.id)

    if user_session:
        session_id = user_session.session_id
    else:
        session_id = str(uuid.uuid4())

    return service.get_session_messages(user_id=current_user.id, session_id=session_id)


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

    # 만약 localStorage를 통해 만들어진 session_id가 db에 없다면 create_chat_session으로 넘긴다
    if not service.exist_session(session_id, current_user.id):
        return create_chat_session(db, current_user)

    return service.get_session_messages(user_id=current_user.id, session_id=session_id)


@router.delete(
    "/session",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_chatbot_session(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    현재 로그인한 사용자의 챗봇 세션을 초기화한다.
    """
    service = ChatbotService(db)
    service.delete_user_session(current_user.id)