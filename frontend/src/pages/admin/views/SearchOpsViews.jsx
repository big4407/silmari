/** 검색 운영 뷰 — CCTV 소스·검색 요청·작업·매칭 검수 (목 UI) */
import { useState } from 'react';
import PageHead from '../components/PageHead';
import { StatValue, TableEmptyRow } from '../components/EmptyState';

export function CctvSourceView() {
  const [tab, setTab] = useState('region');

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
  );

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
  );

  const dailyTable = (
    <div className="admin-card admin-table-wrap">
      <div className="admin-card-h">
        일자별 인덱싱 작업 이력{' '}
        <span className="admin-pill admin-pill--muted">
          영상 적재 + 인물 탐지(video · video_detail)
        </span>
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
            <th style={{ textAlign: 'right' }} />
          </tr>
        </thead>
        <tbody>
          <TableEmptyRow colSpan={7} />
        </tbody>
      </table>
    </div>
  );

  return (
    <>
      <PageHead
        viewId="cctv-source"
        desc="전날 적재된 CCTV 영상을 관리합니다. 지역별 커버리지와 일자별 수집 작업 이력을 함께 확인할 수 있습니다."
      />
      {summary}
      <div className="admin-tabbar">
        <button
          type="button"
          className={`admin-tab${tab === 'region' ? ' admin-tab--on' : ''}`}
          onClick={() => setTab('region')}
        >
          지역별 현황
        </button>
        <button
          type="button"
          className={`admin-tab${tab === 'daily' ? ' admin-tab--on' : ''}`}
          onClick={() => setTab('daily')}
        >
          일자별 이력
        </button>
      </div>
      {tab === 'region' ? (
        <>
          <div className="admin-toolbar">
            <select disabled>
              <option>전체 시·도</option>
            </select>
            <input type="date" disabled />
            <div className="admin-spacer" />
          </div>
          {regionTable}
        </>
      ) : (
        <>
          <div className="admin-toolbar">
            <input type="date" disabled />
            <select disabled>
              <option>전체 상태</option>
            </select>
            <div className="admin-spacer" />
            <button type="button" className="admin-btn" disabled>
              인덱싱 재시도
            </button>
          </div>
          {dailyTable}
        </>
      )}
    </>
  );
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
        <select disabled>
          <option>전체 유형</option>
        </select>
        <select disabled>
          <option>전체 요청자</option>
        </select>
        <input type="date" disabled />
        <div className="admin-spacer" />
        <button type="button" className="admin-btn" disabled>
          CSV보내기
        </button>
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
              <th style={{ textAlign: 'right' }} />
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
  );
}
