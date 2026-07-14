/** LLM 운영 뷰 — 사용량·비용·성능·로그 (목 UI) */
import PageHead from '../components/PageHead';
import EmptyState, { StatValue, TableEmptyRow } from '../components/EmptyState';

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
  );
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
        <select disabled>
          <option>전체 유형</option>
        </select>
        <select disabled>
          <option>전체 모델</option>
        </select>
        <select disabled>
          <option>전체 상태</option>
        </select>
        <div className="admin-spacer" />
        <button type="button" className="admin-btn" disabled>
          CSV보내기
        </button>
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
  );
}
