import PageHead from "../components/PageHead"
import EmptyState, { StatValue, TableEmptyRow } from "../components/EmptyState"

export function DashboardView() {
  return (
    <>
      <PageHead
        viewId="dashboard"
        desc="오늘의 운영 현황 요약입니다. 처리 대기 항목과 시스템 상태를 한눈에 확인하세요."
      />
      <div className="admin-stat-grid">
        <div className="admin-stat admin-stat--amber">
          <div className="admin-label">가입 승인 대기</div>
          <StatValue unit="건" />
        </div>
        <div className="admin-stat">
          <div className="admin-label">진행 중 실종 사건</div>
          <StatValue unit="건" />
        </div>
        <div className="admin-stat admin-stat--green">
          <div className="admin-label">오늘 검색 작업</div>
          <StatValue unit="건" />
        </div>
        <div className="admin-stat admin-stat--red">
          <div className="admin-label">LLM 오류율 (24h)</div>
          <StatValue unit="%" />
        </div>
      </div>
      <div className="admin-cols">
        <div className="admin-card">
          <div className="admin-card-h">검색 작업 현황</div>
          <div className="admin-card-b admin-table-wrap">
            <table>
              <thead>
                <tr>
                  <th>작업 ID</th>
                  <th>사건</th>
                  <th>대상 CCTV</th>
                  <th>진행</th>
                  <th>상태</th>
                </tr>
              </thead>
              <tbody>
                <TableEmptyRow colSpan={5} />
              </tbody>
            </table>
          </div>
        </div>
        <div className="admin-card">
          <div className="admin-card-h">최근 관리자 활동</div>
          <div className="admin-card-b">
            <EmptyState message="최근 관리자 활동이 없습니다." />
          </div>
        </div>
      </div>
    </>
  )
}
