function formatDateTime(value) {
  return value ? new Date(value).toLocaleString() : '-';
}

function formatCost(value) {
  return value == null ? '-' : `$${Number(value).toFixed(6)}`;
}

export function LlmConversationRow({ conversation, onOpen }) {
  const totalTokens =
    (conversation.input_tokens ?? 0) + (conversation.output_tokens ?? 0);

  return (
    <tr>
      <td>{formatDateTime(conversation.last_called_at)}</td>
      <td>챗봇 대화</td>
      <td>{conversation.username ?? '-'}</td>
      <td>{conversation.model}</td>
      <td>{conversation.search_id}</td>
      <td>{conversation.call_count.toLocaleString()}건</td>
      <td>{totalTokens.toLocaleString()}</td>
      <td>
        {conversation.avg_latency_ms == null
          ? '-'
          : `${Math.round(conversation.avg_latency_ms).toLocaleString()}ms`}
      </td>
      <td>{formatCost(conversation.cost)}</td>
      <td>
        <button
          className="admin-btn"
          type="button"
          onClick={() => onOpen(conversation.chatbot_s_id)}
        >
          상세
        </button>
      </td>
    </tr>
  );
}
