/** 검색 운영 뷰 — CCTV 소스·검색 요청·작업·매칭 검수 (목 UI) */
import { useState } from "react"
import PageHead from "../components/PageHead"
import { StatValue, TableEmptyRow } from "../components/EmptyState"

export function CctvSourceView() {
  const [tab, setTab] = useState("region")

  const summary = (
    <div className="admin-stat-grid">
      <div className="admin-stat">
        <div className="admin-label">수집 지역</div>
        <StatValue unit="구" />
      </div>
      <div className="admin-stat admin-stat--green">
        <div className="admin-label">영상 파일</div>
        <StatValue unit="개" />
      </div>
      <div className="admin-stat">
        <div className="admin-label">총 용량</div>
        <StatValue unit="GB" />
      </div>
      <div className="admin-stat admin-stat--amber">
        <div className="admin-label">⚠ 수집 실패·누락</div>
        <StatValue unit="구" />
      </div>
    </div>
  )

  const regionTable = (
    <div className="admin-card admin-table-wrap">
      <div className="admin-card-h">지역별 수집 현황</div>
      <table>
        <thead>
          <tr>
            <th>지역</th>
            <th>CCTV 대수</th>
            <th>영상 파일</th>
            <th>시간대 커버리지</th>
            <th>용량</th>
            <th>상태</th>
          </tr>
        </thead>
        <tbody>
          <TableEmptyRow colSpan={6} />
        </tbody>
      </table>
    </div>
  )

  const dailyTable = (
    <div className="admin-card admin-table-wrap">
      <div className="admin-card-h">
        일자별 인덱싱 작업 이력{" "}
        <span className="admin-pill admin-pill--muted">영상 적재 + 인물 탐지(video · video_detail)</span>
      </div>
      <table>
        <thead>
          <tr>
            <th>작업 일자</th>
            <th>대상 지역</th>
            <th>영상 적재</th>
            <th>인물 인덱싱</th>
            <th>소요</th>
            <th>상태</th>
            <th style={{ textAlign: "right" }} />
          </tr>
        </thead>
        <tbody>
          <TableEmptyRow colSpan={7} />
        </tbody>
      </table>
    </div>
  )

  return (
    <>
      <PageHead
        viewId="cctv-source"
        desc="전날 적재된 CCTV 영상을 관리합니다. 지역별 커버리지와 일자별 수집 작업 이력을 함께 확인할 수 있습니다."
      />
      {summary}
      <div className="admin-tabbar">
        <button type="button" className={`admin-tab${tab === "region" ? " admin-tab--on" : ""}`} onClick={() => setTab("region")}>
          지역별 현황
        </button>
        <button type="button" className={`admin-tab${tab === "daily" ? " admin-tab--on" : ""}`} onClick={() => setTab("daily")}>
          일자별 이력
        </button>
      </div>
      {tab === "region" ? (
        <>
          <div className="admin-toolbar">
            <select disabled><option>전체 시·도</option></select>
            <input type="date" disabled />
            <div className="admin-spacer" />
          </div>
          {regionTable}
        </>
      ) : (
        <>
          <div className="admin-toolbar">
            <input type="date" disabled />
            <select disabled><option>전체 상태</option></select>
            <div className="admin-spacer" />
            <button type="button" className="admin-btn" disabled>인덱싱 재시도</button>
          </div>
          {dailyTable}
        </>
      )}
    </>
  )
}

export function SearchRequestsView() {
  return (
    <>
      <PageHead
        viewId="search-requests"
        desc="전체 사용자가 요청한 검색 쿼리 이력입니다. 안내문자·챗봇·자동검색 유형별로 어떤 조건이 검색됐는지 사후 조회·집계합니다."
      />
      <div className="admin-stat-grid">
        <div className="admin-stat">
          <div className="admin-label">오늘 검색 요청</div>
          <StatValue unit="건" />
        </div>
        <div className="admin-stat">
          <div className="admin-label">안내문자 파싱</div>
          <StatValue unit="건" />
        </div>
        <div className="admin-stat">
          <div className="admin-label">챗봇 검색</div>
          <StatValue unit="건" />
        </div>
        <div className="admin-stat">
          <div className="admin-label">자동 검색</div>
          <StatValue unit="건" />
        </div>
      </div>
      <div className="admin-toolbar">
        <input placeholder="이름·인상착의·지역 검색" disabled />
        <select disabled><option>전체 유형</option></select>
        <select disabled><option>전체 요청자</option></select>
        <input type="date" disabled />
        <div className="admin-spacer" />
        <button type="button" className="admin-btn" disabled>CSV보내기</button>
      </div>
      <div className="admin-card admin-table-wrap">
        <table>
          <thead>
            <tr>
              <th>요청 ID</th>
              <th>유형</th>
              <th>요청자</th>
              <th>안내문자</th>
              <th>대상자</th>
              <th>인상착의</th>
              <th>실종 지역·시각</th>
              <th>검색 일시</th>
              <th style={{ textAlign: "right" }} />
            </tr>
          </thead>
          <tbody>
            <TableEmptyRow colSpan={9} />
          </tbody>
        </table>
      </div>
      <p className="admin-footnote">
        ※ <code>search</code> 테이블의 요청 이력입니다.
      </p>
    </>
  )
}

export function SearchJobsView() {
  return (
    <>
      <PageHead
        viewId="search-jobs"
        desc="저장된 안내문자와 수집된 CCTV 영상으로 검색 작업을 실행하고 진행 상황을 모니터링합니다."
      />
      <div className="admin-card admin-mb">
        <div className="admin-card-h">새 검색 시작</div>
        <div className="admin-card-b">
          <div className="admin-form-row">
            <div className="admin-fld">
              <label>안내문자(신고)</label>
              <select disabled><option>안내문자를 선택하세요</option></select>
            </div>
            <div className="admin-fld">
              <label>대상 지역</label>
              <select disabled><option>지역을 선택하세요</option></select>
            </div>
            <div className="admin-fld">
              <label>수집 일자</label>
              <input type="date" disabled />
            </div>
            <div className="admin-fld">
              <label>시간대</label>
              <select disabled><option>시간대를 선택하세요</option></select>
            </div>
          </div>
          <div className="admin-form-row" style={{ alignItems: "flex-end" }}>
            <div className="admin-fld">
              <label>매칭 모델</label>
              <select disabled><option>모델을 선택하세요</option></select>
            </div>
            <div className="admin-fld">
              <label>참조사진(선택)</label>
              <input type="text" placeholder="첨부 시 얼굴 기반 보강" disabled />
            </div>
            <div className="admin-fld" style={{ flex: "0 0 auto" }}>
              <label>&nbsp;</label>
              <div style={{ fontSize: "12.5px", color: "var(--admin-ink-2)", padding: "8px 0" }}>
                대상 영상 <b>—</b>개 · 예상 시간 <b>—</b>
              </div>
            </div>
            <div className="admin-spacer" />
            <button type="button" className="admin-btn admin-btn--primary" style={{ flex: "0 0 auto" }} disabled>
              검색 작업 실행
            </button>
          </div>
        </div>
      </div>
      <div className="admin-stat-grid">
        <div className="admin-stat">
          <div className="admin-label">진행 중</div>
          <StatValue />
        </div>
        <div className="admin-stat admin-stat--green">
          <div className="admin-label">오늘 완료</div>
          <StatValue />
        </div>
        <div className="admin-stat admin-stat--amber">
          <div className="admin-label">대기열</div>
          <StatValue />
        </div>
        <div className="admin-stat admin-stat--red">
          <div className="admin-label">실패 (24h)</div>
          <StatValue />
        </div>
      </div>
      <div className="admin-card admin-table-wrap">
        <table>
          <thead>
            <tr>
              <th>작업 ID</th>
              <th>안내문자</th>
              <th>대상 영상 풀</th>
              <th>모델</th>
              <th>진행</th>
              <th>상태</th>
              <th>시작</th>
            </tr>
          </thead>
          <tbody>
            <TableEmptyRow colSpan={7} />
          </tbody>
        </table>
      </div>
    </>
  )
}

export function MatchReviewView() {
  return (
    <>
      <PageHead
        viewId="match-review"
        desc="검색이 찾은 후보(탐지된 인물 이미지)를 검토합니다. YOLO 오탐(마네킹·포스터 등)은 선택해 일괄 제외하고, 확정은 행을 클릭해 상세에서 진행합니다."
      />
      <div className="admin-toolbar">
        <select disabled><option>검색 작업을 선택하세요</option></select>
        <select disabled><option>유사도 높은 순</option></select>
        <div className="admin-spacer" />
        <span className="admin-pill admin-pill--muted">후보 — · 확정 — · 제외 —</span>
      </div>
      <div className="admin-card admin-table-wrap">
        <table>
          <thead>
            <tr>
              <th style={{ width: 34 }}><input type="checkbox" aria-label="전체 선택" disabled /></th>
              <th>순위</th>
              <th>썸네일</th>
              <th>CCTV / 위치</th>
              <th>발견 시각</th>
              <th>유사도</th>
              <th>인상착의 일치</th>
              <th style={{ textAlign: "right" }}>제외</th>
            </tr>
          </thead>
          <tbody>
            <TableEmptyRow colSpan={8} message="검색 작업을 선택하면 후보 목록이 표시됩니다." />
          </tbody>
        </table>
      </div>
    </>
  )
}
