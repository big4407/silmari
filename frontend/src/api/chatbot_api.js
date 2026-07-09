import client from './client';

export const sendChatMessage = async ({ sessionId, message }) => {
  const response = await client.post('/chatbot/chat', {
    session_id: sessionId,
    message,
  });

  return response.data;
};
