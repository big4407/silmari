import client from './client.js';

export async function getLlmUsageSummary() {
  const response = await client.get('/llm_call/summary');
  return response.data;
}

export async function getLlmCallList({
  page = 1,
  perPage = 20,
  callType,
  searchId,
  userId,
  modelName,
  status,
  startDate,
  endDate,
  orderBy = 'latest',
}) {
  const params = {
    page,
    size: perPage,
    call_type: callType,
    order_by: orderBy,
  };

  if (searchId) params.search_id = searchId;
  if (userId) params.user_id = userId;
  if (modelName) params.model_name = modelName;
  if (status) params.status = status;
  if (startDate) params.start_date = startDate;
  if (endDate) params.end_date = endDate;

  const response = await client.get('/llm_call/admin', {
    params,
  });

  return response.data;
}

export async function getLlmConversation(chatbotSessionId) {
  const response = await client.get(
    `/llm_call/admin/chatbot/${chatbotSessionId}`,
  );

  return response.data;
}

export async function getLlmMessageCallDetail(llmCallId) {
  const response = await client.get(`/llm_call/admin/message/${llmCallId}`);

  return response.data;
}
