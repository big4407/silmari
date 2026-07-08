import axios from 'axios';

const api = axios.create({
  baseURL: 'http://localhost:8000',
});

export const sendChatMessage = async ({ sessionId, message }) => {
  const response = await api.post('/chatbot/chat', {
    session_id: sessionId,
    message,
  });

  return response.data;
};
