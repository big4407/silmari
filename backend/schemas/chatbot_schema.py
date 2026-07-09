from pydantic import BaseModel


class ChatbotRequest(BaseModel):
    session_id: str
    message: str


class ChatbotResponse(BaseModel):
    response: str
    session_id: str
