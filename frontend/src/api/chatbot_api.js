import axios from 'axios';

import { tokenStore } from './client.js';

const token = tokenStore.getAccess();
const api = axios.create({
  baseURL: 'http://localhost:8000',
});

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

export const getChatSession = async (sessionId) => {
  const {data} = await api.get(`/chatbot/session/${sessionId}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
  return data;
};
