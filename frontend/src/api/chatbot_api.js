import client from './client.js';

// 챗봇에 메시지를 보내는 요청을 보내고 응답을 받아와서 data를 반환
export const sendChatMessage = async ({ sessionId, message }) => {
  const response = await client.post('/chatbot/chat', {
    session_id: sessionId,
    message,
  });

  return response.data;
};

// 챗봇과의 채팅세션을 불러오기 위한 함수
export const getChatSession = async (sessionId) => {
  const url = sessionId ? `/chatbot/session/${sessionId}` : `/chatbot/session`;

  const { data } = await client.get(url);

  return data;
};

// 세션 삭제를 위한 함수
export const deleteChatSession = async () => {
  const response = await client.delete('/chatbot/session');

  return response.data;
};