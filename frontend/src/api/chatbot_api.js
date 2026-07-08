import axios from 'axios';

import { tokenStore } from './client.js';

const token = tokenStore.getAccess();
const api = axios.create({
  baseURL: 'http://localhost:8000',
});

// 챗봇에 메시지를 보내는 요청을 보내고 응답을 받아와서 data를 반환
export const sendChatMessage = async ({ sessionId, message }) => {
  const response = await api.post(
    '/chatbot/chat',
    {
      session_id: sessionId,
      message,
    },
    {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    },
  );

  return response.data;
};

// 챗봇과의 채팅세션을 불러오기 위한 함수
export const getChatSession = async (sessionId) => {
  const {data} = await api.get(`/chatbot/session/${sessionId}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
  return data;
};
