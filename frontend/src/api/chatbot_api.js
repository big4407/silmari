/**
 * 챗봇 API — POST /api/chatbot/chat
 * DevChatbotPage, ChatbotPage에서 사용.
 */
import axios from 'axios';
import { API_BASE, API_PREFIX } from './client';

const api = axios.create({
  baseURL: API_BASE,
});

export const sendChatMessage = async ({ sessionId, message }) => {
  const response = await api.post(`${API_PREFIX}/chatbot/chat`, {
    session_id: sessionId,
    message,
  });

  return response.data;
};
