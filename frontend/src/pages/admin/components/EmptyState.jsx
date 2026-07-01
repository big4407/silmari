/** 관리자 콘솔 공통 빈 상태·통계·테이블 플레이스홀더 컴포넌트 */
export function TableEmptyRow({ colSpan, message = "데이터가 없습니다." }) {
  return (
    <tr className="admin-table-empty">
      <td colSpan={colSpan}>{message}</td>
    </tr>
  )
}

export default function EmptyState({
  message = "데이터가 없습니다. DB 연동 후 이 영역에 표시됩니다.",
}) {
  return (
    <div className="admin-empty">
      <p>{message}</p>
    </div>
  )
}

export function StatValue({ value = null, unit }) {
  const hasValue = value !== null && value !== undefined && value !== ""
  return (
    <div className="admin-value">
      {hasValue ? (
        <>
          {value}
          {unit ? <small>{unit}</small> : null}
        </>
      ) : (
        "—"
      )}
    </div>
  )
}
