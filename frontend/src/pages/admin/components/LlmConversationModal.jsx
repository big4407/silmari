export function LlmConversationModal({ open, conversation, loading, onClose }) {
  if (!open) return null;

  return (
    <div className="admin-modal-backdrop">
      <div className="admin-modal">
        <div className="admin-modal-header">
          <h2>챗봇 대화 호출 상세</h2>

          <button type="button" onClick={onClose}>
            닫기
          </button>
        </div>

        {loading ? (
          <div>불러오는 중...</div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>호출 일시</th>
                <th>모델</th>
                <th>프롬프트</th>
                <th>응답</th>
                <th>입력 토큰</th>
                <th>출력 토큰</th>
                <th>응답 시간</th>
                <th>비용</th>
                <th>상태</th>
              </tr>
            </thead>

            <tbody>
              {(conversation?.calls ?? []).map((call) => (
                <tr key={call.id}>
                  <td>{new Date(call.created_at).toLocaleString()}</td>
                  <td>{call.model_name}</td>
                  <td>{call.prompt}</td>
                  <td>{call.response ?? '-'}</td>
                  <td>{call.input_tokens ?? '-'}</td>
                  <td>{call.output_tokens ?? '-'}</td>
                  <td>
                    {call.latency_ms == null ? '-' : `${call.latency_ms}ms`}
                  </td>
                  <td>
                    {call.cost == null
                      ? '-'
                      : `$${Number(call.cost).toFixed(6)}`}
                  </td>
                  <td>{call.status === '1' ? '성공' : '실패'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
