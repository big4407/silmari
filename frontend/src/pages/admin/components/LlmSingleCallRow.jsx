function formatDateTime(value) {
  return value ? new Date(value).toLocaleString() : '-';
}

function formatCost(value) {
  return value == null ? '-' : `$${Number(value).toFixed(6)}`;
}

export function LlmSingleCallRow({ call }) {
  const totalTokens = (call.input_tokens ?? 0) + (call.output_tokens ?? 0);
  const calledAt = formatDateTime(call.first_called_at);
  return (
    <tr>
      <td title={calledAt}>{calledAt}</td>
      <td>인상착의 한영변환</td>
      <td>{call.username ?? '-'}</td>
      <td>{call.model}</td>
      <td>{call.search_id}</td>
      <td>1건</td>
      <td>{totalTokens.toLocaleString()}</td>
      <td>
        {call.total_latency_ms == null
          ? '-'
          : `${call.total_latency_ms.toLocaleString()}ms`}
      </td>
      <td>{formatCost(call.cost)}</td>
      <td>–</td>
    </tr>
  );
}
