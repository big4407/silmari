import PageHead from "../components/PageHead"
import EmptyState, { StatValue, TableEmptyRow } from "../components/EmptyState"

export function RepTimeView() {
  return (
    <>
      <PageHead
        viewId="rep-time"
        desc="실종 발생 시각(search.missing_time)과 안내문자 수신(message.crt_dt)을 기준으로 시간 패턴을 분석합니다."
      />
      <div className="admin-toolbar">
        <select disabled><option>최근 90일</option></select>
        <select disabled><option>실종 발생시각 기준</option></select>
        <div className="admin-spacer" />
        <button type="button" className="admin-btn" disabled>리포트보내기</button>
      </div>
      <div className="admin-cols">
        <div className="admin-card">
          <div className="admin-card-h">시간대별 발생 분포</div>
          <div className="admin-card-b">
            <EmptyState message="분석 데이터가 없습니다." />
          </div>
        </div>
        <div className="admin-card">
          <div className="admin-card-h">요일별 분포</div>
          <div className="admin-card-b">
            <EmptyState message="분석 데이터가 없습니다." />
          </div>
        </div>
      </div>
    </>
  )
}

export function RepRegionView() {
  return (
    <>
      <PageHead
        viewId="rep-region"
        desc="실종 지역(search.missing_location)과 CCTV 커버리지(video.region_code)를 region 기준으로 분석합니다."
      />
      <div className="admin-toolbar">
        <select disabled><option>최근 90일</option></select>
        <select disabled><option>전체 시·도</option></select>
        <div className="admin-spacer" />
        <button type="button" className="admin-btn" disabled>리포트보내기</button>
      </div>
      <div className="admin-card admin-table-wrap">
        <div className="admin-card-h">지역별 실종 발생 · CCTV 커버리지</div>
        <table>
          <thead>
            <tr>
              <th>지역</th>
              <th>실종 발생</th>
              <th>검색 요청</th>
              <th>CCTV 등록</th>
              <th>커버리지</th>
              <th>매칭 성공률</th>
            </tr>
          </thead>
          <tbody>
            <TableEmptyRow colSpan={6} />
          </tbody>
        </table>
      </div>
    </>
  )
}

export function RepSearchView() {
  return (
    <>
      <PageHead
        viewId="rep-search"
        desc="검색 유형별 성능과 매칭 정확도를 분석합니다 (search.search_type · analysis_detail.matching_rate · analysis.analysis_status)."
      />
      <div className="admin-stat-grid">
        <div className="admin-stat">
          <div className="admin-label">총 검색</div>
          <StatValue unit="건" />
        </div>
        <div className="admin-stat admin-stat--green">
          <div className="admin-label">평균 매칭률</div>
          <StatValue unit="%" />
        </div>
        <div className="admin-stat">
          <div className="admin-label">후보 발견율</div>
          <StatValue unit="%" />
        </div>
        <div className="admin-stat admin-stat--amber">
          <div className="admin-label">평균 처리시간</div>
          <StatValue unit="분" />
        </div>
      </div>
      <div className="admin-cols">
        <div className="admin-card">
          <div className="admin-card-h">검색 유형별 성능 (search_type)</div>
          <div className="admin-card-b admin-table-wrap" style={{ paddingTop: 6 }}>
            <table>
              <thead>
                <tr>
                  <th>유형</th>
                  <th>건수</th>
                  <th>평균 매칭률</th>
                  <th>발견율</th>
                </tr>
              </thead>
              <tbody>
                <TableEmptyRow colSpan={4} />
              </tbody>
            </table>
          </div>
        </div>
        <div className="admin-card">
          <div className="admin-card-h">매칭률 구간 분포 (matching_rate)</div>
          <div className="admin-card-b">
            <EmptyState message="분석 데이터가 없습니다." />
          </div>
        </div>
      </div>
    </>
  )
}
