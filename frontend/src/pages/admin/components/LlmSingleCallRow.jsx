function formatDateTime(value) {
  return value ? new Date(value).toLocaleString() : '-';
}

function formatCost(value) {
  return value == null ? '-' : `$${Number(value).toFixed(6)}`;
}

export function LlmSingleCallRow({ call }) {
  const totalTokens = (call.input_tokens ?? 0) + (call.output_tokens ?? 0);

  return (
    <tr>
      <td>{formatDateTime(call.created_at)}</td>
      <td>인상착의 한영변환</td>
      <td>{call.username ?? '-'}</td>
      <td>{call.model_name}</td>
      <td>1건</td>
      <td>{totalTokens.toLocaleString()}</td>
      <td>
        {call.latency_ms == null
          ? '-'
          : `${call.latency_ms.toLocaleString()}ms`}
      </td>
      <td>{formatCost(call.cost)}</td>
      <td>{call.status === '1' ? '성공' : '실패'}</td>
      <td>-</td>
    </tr>
  );
}
