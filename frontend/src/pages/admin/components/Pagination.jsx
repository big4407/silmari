/**
 * 관리자 콘솔 공통 페이지네이션 — 이전/다음 + 숫자 버튼(현재 페이지 중심 5개,
 * 양끝은 … 로 생략) + 총 건수 표시를 한 곳에서 통일해서 쓴다.
 *
 * 이전엔 페이지마다 페이징 UI가 제각각이었다(AuditViews/CaseAssignmentView/
 * LlmViews/MissingPersonCaseViews/SearchOpsViews는 단순 이전·다음뿐이고
 * "총 N건" 문구도 있었다 없었다 했고, MessageViews만 숫자 버튼까지 있었음).
 * 이 컴포넌트가 그 중 가장 완성도 높았던 MessageViews 패턴을 기준으로
 * "총 N건" 문구까지 합쳐서 모든 관리자 목록 페이지의 표준이 된다.
 *
 * @param {number} page 현재 페이지(1-base)
 * @param {number} totalPages 전체 페이지 수(최소 1)
 * @param {number} total 전체 건수 — 없으면 "총 N건" 문구를 생략
 * @param {(nextPage: number) => void} onPageChange
 * @param {boolean} [loading] 로딩 중엔 버튼 비활성화
 * @param {number} [maxVisible] 가운데 보여줄 숫자 버튼 개수(기본 5)
 */
export default function Pagination({
  page,
  totalPages,
  total,
  onPageChange,
  loading = false,
  maxVisible = 5,
}) {
  const safeTotalPages = Math.max(1, totalPages || 1);

  // total이 0(빈 목록)이면 페이지 이동이 의미 없으니 아예 안 그린다.
  if (total !== undefined && total <= 0) return null;

  let start = Math.max(1, page - Math.floor(maxVisible / 2));
  let end = start + maxVisible - 1;
  if (end > safeTotalPages) {
    end = safeTotalPages;
    start = Math.max(1, end - maxVisible + 1);
  }
  const pageNumbers = Array.from(
    { length: end - start + 1 },
    (_, i) => start + i,
  );

  const goTo = (p) => {
    if (p < 1 || p > safeTotalPages || p === page) return;
    onPageChange(p);
  };

  return (
    <div className="admin-pagination">
      <button
        type="button"
        className="admin-btn"
        disabled={page <= 1 || loading}
        onClick={() => goTo(page - 1)}
      >
        이전
      </button>

      {pageNumbers[0] > 1 && (
        <>
          <button
            type="button"
            className="admin-btn"
            disabled={loading}
            onClick={() => goTo(1)}
          >
            1
          </button>
          {pageNumbers[0] > 2 && <span className="admin-pagination__ellipsis">…</span>}
        </>
      )}

      {pageNumbers.map((p) => (
        <button
          key={p}
          type="button"
          className={p === page ? 'admin-btn admin-btn--primary' : 'admin-btn'}
          disabled={loading}
          onClick={() => goTo(p)}
        >
          {p}
        </button>
      ))}

      {pageNumbers[pageNumbers.length - 1] < safeTotalPages && (
        <>
          {pageNumbers[pageNumbers.length - 1] < safeTotalPages - 1 && (
            <span className="admin-pagination__ellipsis">…</span>
          )}
          <button
            type="button"
            className="admin-btn"
            disabled={loading}
            onClick={() => goTo(safeTotalPages)}
          >
            {safeTotalPages}
          </button>
        </>
      )}

      <button
        type="button"
        className="admin-btn"
        disabled={page >= safeTotalPages || loading}
        onClick={() => goTo(page + 1)}
      >
        다음
      </button>

      {total !== undefined && (
        <span className="admin-pill admin-pill--muted admin-pagination__total">
          {page} / {safeTotalPages} (총 {total.toLocaleString()}건)
        </span>
      )}
    </div>
  );
}
