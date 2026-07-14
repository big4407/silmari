import { TableEmptyRow } from './EmptyState';
import { LlmSingleCallRow } from './LlmSingleCallRow';
import { LlmConversationRow } from './LlmConversationRow';

export function LlmCallList({
  items = [],
  onOpenConversation,
  onOpenSingleCall,
}) {
  return (
    items && (
      <table>
        <thead>
          <tr>
            <th>호출 일시</th>
            <th>유형</th>
            <th>사용자</th>
            <th>모델명</th>
            <th>검색 ID</th>
            <th>호출 수</th>
            <th>토큰</th>
            <th>응답 시간</th>
            <th>비용</th>
            <th>상세</th>
          </tr>
        </thead>

        <tbody>
          {items.length === 0 ? (
            <TableEmptyRow colSpan={8} />
          ) : (
            items.map((item, index) =>
              item.call_type === '2' ? (
                <LlmConversationRow
                  key={item.row_key} //index를 임시로 key로 사용
                  conversation={item}
                  onOpen={onOpenConversation}
                />
              ) : (
                <LlmSingleCallRow
                  key={item.row_key} //index를 임시로 key로 사용
                  call={item}
                  onOpen={onOpenSingleCall}
                />
              ),
            )
          )}
        </tbody>
      </table>
    )
  );
}
