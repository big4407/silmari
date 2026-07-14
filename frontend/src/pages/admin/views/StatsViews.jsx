/** 통계 뷰 — CCTV 영상·검색·인구통계·내보내기 (목 UI, 분석 리포트 대체) */
import PageHead from '../components/PageHead';
import EmptyState, { StatValue, TableEmptyRow } from '../components/EmptyState';

export function CctvStatsView() {
  return (
    <>
      <PageHead
        viewId="stats-cctv"
        desc="인덱싱된 CCTV 영상 현황을 집계합니다 (video · video_detail 기준)."
      />
      <div className="admin-toolbar">
        <select disabled>
          <option>최근 90일</option>
        </select>
        <select disabled>
          <option>전체 지역</option>
        </select>
        <div className="admin-spacer" />
      </div>
      <div className="admin-stat-grid">
        <div className="admin-stat">
          <div className="admin-label">등록 영상</div>
          <StatValue unit="건" />
        </div>
        <div className="admin-stat admin-stat--green">
          <div className="admin-label">인덱싱 완료</div>
          <StatValue unit="건" />
        </div>
        <div className="admin-stat">
          <div className="admin-label">탐지된 인물</div>
          <StatValue unit="명" />
        </div>
        <div className="admin-stat admin-stat--amber">
          <div className="admin-label">CCTV 커버 지역</div>
          <StatValue unit="곳" />
        </div>
      </div>
      <div className="admin-card admin-table-wrap">
        <div className="admin-card-h">지역별 영상 등록 현황</div>
        <table>
          <thead>
            <tr>
              <th>지역</th>
              <th>등록 영상</th>
              <th>인덱싱 완료</th>
              <th>탐지 인물</th>
            </tr>
          </thead>
          <tbody>
            <TableEmptyRow colSpan={4} />
          </tbody>
        </table>
      </div>
    </>
  );
}

export function SearchStatsView() {
  return (
    <>
      <PageHead
        viewId="stats-search"
        desc="검색 요청과 매칭 결과를 집계합니다 (search · analysis · analysis_detail 기준)."
      />
      <div className="admin-toolbar">
        <select disabled>
          <option>최근 90일</option>
        </select>
        <select disabled>
          <option>전체 검색 유형</option>
        </select>
        <div className="admin-spacer" />
      </div>
      <div className="admin-stat-grid">
        <div className="admin-stat">
          <div className="admin-label">총 검색 요청</div>
          <StatValue unit="건" />
        </div>
        <div className="admin-stat admin-stat--green">
          <div className="admin-label">매칭 성공</div>
          <StatValue unit="건" />
        </div>
        <div className="admin-stat">
          <div className="admin-label">평균 유사도</div>
          <StatValue unit="%" />
        </div>
        <div className="admin-stat admin-stat--amber">
          <div className="admin-label">평균 처리시간</div>
          <StatValue unit="초" />
        </div>
      </div>
      <div className="admin-cols">
        <div className="admin-card">
          <div className="admin-card-h">검색 유형별 현황 (search_type)</div>
          <div
            className="admin-card-b admin-table-wrap"
            style={{ paddingTop: 6 }}
          >
            <table>
              <thead>
                <tr>
                  <th>유형</th>
                  <th>건수</th>
                  <th>매칭 성공률</th>
                </tr>
              </thead>
              <tbody>
                <TableEmptyRow colSpan={3} />
              </tbody>
            </table>
          </div>
        </div>
        <div className="admin-card">
          <div className="admin-card-h">일별 검색 추이</div>
          <div className="admin-card-b">
            <EmptyState message="통계 데이터가 없습니다." />
          </div>
        </div>
      </div>
    </>
  );
}

export function DemographicStatsView() {
  return (
    <>
      <PageHead
        viewId="stats-demographic"
        desc="성별·연령·지역별 실종·검색 비율을 집계합니다 (search.gender · search.age · search.missing_location 기준)."
      />
      <div className="admin-toolbar">
        <select disabled>
          <option>최근 90일</option>
        </select>
        <div className="admin-spacer" />
      </div>
      <div className="admin-cols">
        <div className="admin-card">
          <div className="admin-card-h">성별 분포</div>
          <div className="admin-card-b">
            <EmptyState message="통계 데이터가 없습니다." />
          </div>
        </div>
        <div className="admin-card">
          <div className="admin-card-h">연령대별 분포</div>
          <div className="admin-card-b">
            <EmptyState message="통계 데이터가 없습니다." />
          </div>
        </div>
      </div>
      <div className="admin-card admin-table-wrap admin-mb">
        <div className="admin-card-h">지역별 실종·검색 비율</div>
        <table>
          <thead>
            <tr>
              <th>지역</th>
              <th>실종 발생</th>
              <th>검색 요청</th>
              <th>검색율</th>
            </tr>
          </thead>
          <tbody>
            <TableEmptyRow colSpan={4} />
          </tbody>
        </table>
      </div>
    </>
  );
}

export function StatsExportView() {
  return (
    <>
      <PageHead
        viewId="stats-export"
        desc="통계 데이터를 표준 형식으로 내보냅니다. 내보내기 이력은 감사 로그에 기록됩니다."
      />
      <div className="admin-card admin-mb">
        <div className="admin-card-h">내보내기</div>
        <div className="admin-card-b">
          <div className="admin-form-row">
            <div className="admin-fld">
              <label>통계 종류</label>
              <select disabled>
                <option>CCTV 영상 통계</option>
                <option>검색 통계</option>
                <option>성별·연령·지역별 통계</option>
              </select>
            </div>
            <div className="admin-fld">
              <label>기간</label>
              <input type="date" disabled />
            </div>
            <div className="admin-fld">
              <label>형식</label>
              <select disabled>
                <option>CSV</option>
              </select>
            </div>
            <div className="admin-fld" style={{ flex: '0 0 auto' }}>
              <label>&nbsp;</label>
              <button
                type="button"
                className="admin-btn admin-btn--primary"
                disabled
              >
                내보내기
              </button>
            </div>
          </div>
        </div>
      </div>
      <div className="admin-card admin-table-wrap">
        <div className="admin-card-h">최근 내보내기</div>
        <table>
          <thead>
            <tr>
              <th>일시</th>
              <th>통계 종류</th>
              <th>기간</th>
              <th>형식</th>
              <th>요청자</th>
              <th style={{ textAlign: 'right' }} />
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
