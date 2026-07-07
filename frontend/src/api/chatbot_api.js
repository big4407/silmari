/**
 * 챗봇 API — POST /api/chatbot/chat
 * DevChatbotPage, ChatbotPage에서 사용.
 */
import axios from 'axios';
import { API_BASE, API_V1 } from './client';

const api = axios.create({
  baseURL: API_BASE,
});

/** 세션 ID와 사용자 메시지를 보내고 봇 응답(JSON)을 반환 */
export const sendChatMessage = async ({ sessionId, message }) => {
  const response = await api.post(`${API_V1}/chatbot/chat`, {
    session_id: sessionId,
    message,
  });

  return response.data;
};
