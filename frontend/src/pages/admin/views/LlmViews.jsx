/** LLM 운영 뷰 — 사용량·비용·성능·로그 (목 UI) */
import PageHead from "../components/PageHead"
import EmptyState, { StatValue, TableEmptyRow } from "../components/EmptyState"

export function LlmUsageView() {
  return (
    <>
      <PageHead
        viewId="llm-usage"
        desc="LLM 호출(llm_call)을 모델·유형별로 집계합니다. 인상착의 한영변환과 챗봇 호출이 구분됩니다."
      />
      <div className="admin-stat-grid">
        <div className="admin-stat">
          <div className="admin-label">오늘 총 호출</div>
          <StatValue unit="건" />
        </div>
        <div className="admin-stat">
          <div className="admin-label">한영변환 (type 1)</div>
          <StatValue unit="건" />
        </div>
        <div className="admin-stat">
          <div className="admin-label">챗봇 (type 2)</div>
          <StatValue unit="건" />
        </div>
        <div className="admin-stat admin-stat--green">
          <div className="admin-label">성공률</div>
          <StatValue unit="%" />
        </div>
      </div>
      <div className="admin-card admin-table-wrap">
        <div className="admin-card-h">모델별 사용량 (오늘)</div>
        <table>
          <thead>
            <tr>
              <th>모델</th>
              <th>용도(call_type)</th>
              <th>호출 수</th>
              <th>비중</th>
              <th>평균 토큰</th>
              <th>성공률</th>
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

export function LlmCostView() {
  return (
    <>
      <PageHead
        viewId="llm-cost"
        desc="호출별 토큰 소비와 환산 비용(cost)을 집계합니다. 비용은 호출 시점 단가로 저장됩니다."
      />
      <div className="admin-stat-grid">
        <div className="admin-stat">
          <div className="admin-label">오늘 입력 토큰</div>
          <StatValue />
        </div>
        <div className="admin-stat">
          <div className="admin-label">오늘 출력 토큰</div>
          <StatValue />
        </div>
        <div className="admin-stat admin-stat--amber">
          <div className="admin-label">오늘 비용</div>
          <StatValue />
        </div>
        <div className="admin-stat">
          <div className="admin-label">이번 달 누적</div>
          <StatValue />
        </div>
      </div>
      <div className="admin-card admin-table-wrap">
        <div className="admin-card-h">모델별 토큰·비용 (이번 달)</div>
        <table>
          <thead>
            <tr>
              <th>모델</th>
              <th>호출 수</th>
              <th>입력 토큰</th>
              <th>출력 토큰</th>
              <th>비용</th>
              <th>비중</th>
            </tr>
          </thead>
          <tbody>
            <TableEmptyRow colSpan={6} />
          </tbody>
        </table>
      </div>
      <p className="admin-footnote">
        ※ <code>input_tokens · output_tokens · cost</code> 합산.
      </p>
    </>
  )
}

export function LlmPerfView() {
  return (
    <>
      <PageHead
        viewId="llm-perf"
        desc="응답 지연(latency_ms)과 오류율(status)을 모니터링합니다. 기준선 초과 시 경보합니다."
      />
      <div className="admin-stat-grid">
        <div className="admin-stat admin-stat--green">
          <div className="admin-label">평균 응답시간</div>
          <StatValue />
        </div>
        <div className="admin-stat">
          <div className="admin-label">P95 응답시간</div>
          <StatValue />
        </div>
        <div className="admin-stat admin-stat--red">
          <div className="admin-label">오류율 (24h)</div>
          <StatValue unit="%" />
        </div>
        <div className="admin-stat admin-stat--amber">
          <div className="admin-label">실패 호출</div>
          <StatValue unit="건" />
        </div>
      </div>
      <div className="admin-cols">
        <div className="admin-card">
          <div className="admin-card-h">모델별 성능</div>
          <div className="admin-card-b admin-table-wrap" style={{ paddingTop: 6 }}>
            <table>
              <thead>
                <tr>
                  <th>모델</th>
                  <th>평균</th>
                  <th>P95</th>
                  <th>오류율</th>
                </tr>
              </thead>
              <tbody>
                <TableEmptyRow colSpan={4} />
              </tbody>
            </table>
          </div>
        </div>
        <div className="admin-card">
          <div className="admin-card-h">최근 오류 (status=0)</div>
          <div className="admin-card-b">
            <EmptyState message="최근 오류가 없습니다." />
          </div>
        </div>
      </div>
    </>
  )
}

export function LlmLogsView() {
  return (
    <>
      <PageHead
        viewId="llm-logs"
        desc="LLM 호출의 프롬프트·응답 원문을 조회합니다. 특히 인상착의 한영변환이 정확한지 검증해 FashionCLIP 검색 품질을 관리합니다."
      />
      <div className="admin-toolbar">
        <input placeholder="프롬프트·응답·검색 ID 검색" disabled />
        <select disabled><option>전체 유형</option></select>
        <select disabled><option>전체 모델</option></select>
        <select disabled><option>전체 상태</option></select>
        <div className="admin-spacer" />
        <button type="button" className="admin-btn" disabled>CSV보내기</button>
      </div>
      <div className="admin-card admin-table-wrap">
        <table>
          <thead>
            <tr>
              <th>호출 ID</th>
              <th>유형</th>
              <th>모델</th>
              <th>연계 검색</th>
              <th>프롬프트 → 응답</th>
              <th>토큰</th>
              <th>지연</th>
              <th>상태</th>
            </tr>
          </thead>
          <tbody>
            <TableEmptyRow colSpan={8} />
          </tbody>
        </table>
      </div>
    </>
  )
}
