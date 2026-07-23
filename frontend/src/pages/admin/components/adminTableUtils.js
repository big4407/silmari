/**
 * 관리자 콘솔 테이블 공통 치수.
 *
 * 처음엔 카드(.admin-table-wrap) 자체에 min-height를 줘서 행이 적어도 흰
 * 박스가 기본 줄 수만큼 늘어나게 했는데, 실제 데이터가 몇 줄 없을 때 빈
 * 흰 배경이 어색하게 남는 문제가 있었다. 올바른 동작은: 카드는 실제 행
 * 개수만큼만 자연스러운 높이로 보여주고, 그 아래 Pagination만 "기본 줄
 * 수를 다 채웠을 때"의 위치에 고정하는 것 — 카드와 Pagination 사이 남는
 * 공간은 빈 흰 박스가 아니라 그냥 페이지 배경으로 보여야 한다.
 *
 * 이를 위해 카드 자체가 아니라, {카드 + Pagination}을 감싸는 바깥
 * 컨테이너에 이 minHeight를 주고 flex column + space-between으로 배치한다
 * (adminPinnedPaginationStyle 참고) — 카드는 자연 높이, Pagination은
 * 컨테이너 하단에 고정된다.
 */
export const ADMIN_TABLE_ROW_HEIGHT = 40;

/**
 * @param {number} pageSize 한 페이지에 보여줄 행 수
 * @returns {number} 헤더 1행 + 본문 pageSize행 기준 예약 높이(px)
 */
export function adminTableMinHeight(pageSize) {
  return ADMIN_TABLE_ROW_HEIGHT * (pageSize + 1);
}

/**
 * {카드 + Pagination}을 감싸는 바깥 div에 그대로 스프레드해서 쓰는 스타일.
 * 카드는 원래 높이 그대로 두고(내부에 minHeight를 주지 않음), Pagination만
 * 이 컨테이너 맨 아래에 고정된다.
 *
 * 사용 예:
 *   <div style={adminPinnedPaginationStyle(PAGE_SIZE)}>
 *     <div className="admin-card admin-table-wrap">...테이블...</div>
 *     <Pagination ... />
 *   </div>
 */
export function adminPinnedPaginationStyle(pageSize) {
  return {
    minHeight: adminTableMinHeight(pageSize),
    display: 'flex',
    flexDirection: 'column',
    justifyContent: 'space-between',
  };
}
