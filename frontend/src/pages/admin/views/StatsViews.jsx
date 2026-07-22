/** 통계 뷰 — CCTV·검색·성별연령지역·발견해결결과·내보내기 (전부 연동) */
import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';

import PageHead from '../components/PageHead';
import { TableEmptyRow } from '../components/EmptyState';
import { SimpleBars } from '../components/SimpleBars';
import { SimpleLineChart } from '../components/SimpleLineChart';
import { StatsFilter } from '../components/StatsFilter';
import {
  exportStats,
  fetchCctvStats,
  fetchDemographicStats,
  fetchExportLogs,
  fetchOutcomeStats,
  fetchSearchStats,
} from '../../../api/client';

const STAT_TYPE_LABELS = {
  cctv: 'CCTV 통계',
  search: '검색 통계',
  demographic: '인구 통계',
  outcomes: '처리 결과 통계',
};

function formatDateInput(date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

function recentDateRange(days) {
  const toDate = new Date();
  const fromDate = new Date();
  fromDate.setDate(toDate.getDate() - days + 1);
  return {
    fromDate: formatDateInput(fromDate),
    toDate: formatDateInput(toDate),
  };
}

function formatDateTime(value) {
  return new Intl.DateTimeFormat('ko-KR', {
    dateStyle: 'short',
    timeStyle: 'short',
  }).format(new Date(value));
}

/** 통계 API 공통 조회 훅 — 로딩/에러 상태 + 요청 도중 화면이 바뀌면 취소(AbortController). */
function useStatsQuery(loader, dependencies) {
  const [state, setState] = useState({
    data: null,
    loading: true,
    error: null,
  });

  useEffect(() => {
    const controller = new AbortController();
    setState((current) => ({ ...current, loading: true, error: null }));

    loader(controller.signal)
      .then((data) => {
        if (!controller.signal.aborted)
          setState({ data, loading: false, error: null });
      })
      .catch((error) => {
        if (controller.signal.aborted) return;
        setState({
          data: null,
          loading: false,
          error:
            error instanceof Error
              ? error.message
              : '통계 조회에 실패했습니다.',
        });
      });

    return () => controller.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, dependencies);

  return state;
}

function formatMetricValue(value, decimals = 0) {
  if (value === null || value === undefined || Number.isNaN(value)) return '--';
  return decimals > 0 ? value.toFixed(decimals) : value.toLocaleString();
}

function formatSearchType(value) {
  return { 1: '안내문자', 2: '챗봇', 3: '자동 검색' }[value] ?? value;
}

function StatCard({
  label,
  value,
  unit,
  loading,
  decimals = 0,
  className = '',
}) {
  return (
    <div className={`admin-stat ${className}`.trim()}>
      <div className="admin-label">{label}</div>
      <div className="admin-value">
        {loading ? '집계 중' : formatMetricValue(value, decimals)}
        {unit ? <small>{unit}</small> : null}
      </div>
    </div>
  );
}

export function CctvStatsView() {
  const [days, setDays] = useState(90);
  const [region, setRegion] = useState('');
  const range = useMemo(() => recentDateRange(days), [days]);

  const state = useStatsQuery(
    (signal) =>
      fetchCctvStats({ ...range, region: region || undefined }, signal),
    [range.fromDate, range.toDate, region],
  );

  return (
    <>
      <PageHead
        viewId="stats-cctv"
        desc="기간별 CCTV 등록, 인덱스 완료, 감지 인원 통계를 조회합니다."
      />

      <StatsFilter
        periodDays={days}
        onPeriodDaysChange={setDays}
        region={region}
        onRegionChange={setRegion}
      />

      {state.error && <div className="stats-error">{state.error}</div>}

      <div className="admin-stat-grid">
        <StatCard
          label="등록 영상"
          value={state.data?.summary.registered_videos}
          unit="건"
          loading={state.loading}
        />
        <StatCard
          label="인덱스 완료"
          value={state.data?.summary.indexed_videos}
          unit="건"
          loading={state.loading}
          className="admin-stat--green"
        />
        <StatCard
          label="감지 인원"
          value={state.data?.summary.detected_persons}
          unit="명"
          loading={state.loading}
        />
        <StatCard
          label="커버 지역"
          value={state.data?.summary.covered_regions}
          unit="곳"
          loading={state.loading}
          className="admin-stat--amber"
        />
      </div>

      <div className="admin-card admin-table-wrap">
        <div className="admin-card-h">지역별 등록 현황</div>
        <table>
          <thead>
            <tr>
              <th>지역</th>
              <th>등록 영상</th>
              <th>인덱스 완료</th>
              <th>감지 인원</th>
            </tr>
          </thead>
          <tbody>
            {state.data?.by_region.length ? (
              state.data.by_region.map((row) => (
                <tr key={row.region}>
                  <td>{row.region}</td>
                  <td>{row.registered_videos.toLocaleString()}</td>
                  <td>{row.indexed_videos.toLocaleString()}</td>
                  <td>{row.detected_persons.toLocaleString()}</td>
                </tr>
              ))
            ) : (
              <TableEmptyRow colSpan={4} />
            )}
          </tbody>
        </table>
      </div>
    </>
  );
}

export function SearchStatsView() {
  const [days, setDays] = useState(90);
  const [searchType, setSearchType] = useState('');
  const range = useMemo(() => recentDateRange(days), [days]);

  const state = useStatsQuery(
    (signal) =>
      fetchSearchStats(
        { ...range, searchType: searchType || undefined },
        signal,
      ),
    [range.fromDate, range.toDate, searchType],
  );

  return (
    <>
      <PageHead
        viewId="stats-search"
        desc="검색 요청과 매칭 성과를 기간별로 집계합니다."
      />

      <StatsFilter
        periodDays={days}
        onPeriodDaysChange={setDays}
        searchType={searchType}
        onSearchTypeChange={setSearchType}
      />

      {state.error && <div className="stats-error">{state.error}</div>}

      <div className="admin-stat-grid">
        <StatCard
          label="총 검색 요청"
          value={state.data?.summary.total_searches}
          unit="건"
          loading={state.loading}
        />
        <StatCard
          label="성공 매칭"
          value={state.data?.summary.successful_matches}
          unit="건"
          loading={state.loading}
          className="admin-stat--green"
        />
        <StatCard
          label="평균 유사도"
          value={state.data?.summary.average_similarity_percent}
          unit="%"
          decimals={1}
          loading={state.loading}
        />
        <StatCard
          label="평균 처리 시간"
          value={state.data?.summary.average_processing_seconds}
          unit="초"
          decimals={2}
          loading={state.loading}
          className="admin-stat--amber"
        />
      </div>

      <div className="admin-cols">
        <div className="admin-card">
          <div className="admin-card-h">검색 유형별 성과</div>
          <div className="admin-card-b admin-table-wrap">
            <table>
              <thead>
                <tr>
                  <th>유형</th>
                  <th>건수</th>
                  <th>성공 건수</th>
                  <th>성공률</th>
                </tr>
              </thead>
              <tbody>
                {state.data?.by_type.length ? (
                  state.data.by_type.map((row) => (
                    <tr key={row.search_type}>
                      <td>{formatSearchType(row.search_type)}</td>
                      <td>{row.count.toLocaleString()}</td>
                      <td>{row.successful_matches.toLocaleString()}</td>
                      <td>{row.success_rate.toFixed(1)}%</td>
                    </tr>
                  ))
                ) : (
                  <TableEmptyRow colSpan={4} />
                )}
              </tbody>
            </table>
          </div>
        </div>

        <div className="admin-card">
          <div className="admin-card-h">일별 검색 추이</div>
          <div className="admin-card-b">
            <SimpleLineChart data={state.data?.daily ?? []} />
          </div>
        </div>
      </div>
    </>
  );
}

export function DemographicStatsView() {
  const [days, setDays] = useState(90);
  const range = useMemo(() => recentDateRange(days), [days]);

  const state = useStatsQuery(
    (signal) => fetchDemographicStats(range, signal),
    [range.fromDate, range.toDate],
  );

  return (
    <>
      <PageHead
        viewId="stats-demographic"
        desc="성별, 연령, 지역별 검색과 처리 결과를 집계합니다."
      />

      <StatsFilter periodDays={days} onPeriodDaysChange={setDays} />

      {state.error && <div className="stats-error">{state.error}</div>}

      <div className="admin-cols">
        <div className="admin-card">
          <div className="admin-card-h">성별 분포</div>
          <div className="admin-card-b">
            <SimpleBars items={state.data?.gender_distribution ?? []} />
          </div>
        </div>

        <div className="admin-card">
          <div className="admin-card-h">연령대 분포</div>
          <div className="admin-card-b">
            <SimpleBars items={state.data?.age_distribution ?? []} />
          </div>
        </div>
      </div>

      <div className="admin-card admin-table-wrap stats-region-table admin-mt">
        <div className="admin-card-h">지역별 처리 현황</div>
        <table>
          <thead>
            <tr>
              <th>지역</th>
              <th>검색 요청</th>
              <th>해결</th>
              <th>해결율</th>
            </tr>
          </thead>
          <tbody>
            {state.data?.by_region.length ? (
              state.data.by_region.map((row) => (
                <tr key={row.region}>
                  <td>{row.region}</td>
                  <td>{row.search_requests.toLocaleString()}</td>
                  <td>{row.resolved_cases.toLocaleString()}</td>
                  <td>{row.resolution_rate.toFixed(1)}%</td>
                </tr>
              ))
            ) : (
              <TableEmptyRow colSpan={4} />
            )}
          </tbody>
        </table>
      </div>
    </>
  );
}

export function OutcomeStatsView() {
  const [days, setDays] = useState(90);
  const [region, setRegion] = useState('');
  const range = useMemo(() => recentDateRange(days), [days]);

  const state = useStatsQuery(
    (signal) =>
      fetchOutcomeStats({ ...range, region: region || undefined }, signal),
    [range.fromDate, range.toDate, region],
  );

  return (
    <>
      <PageHead
        viewId="stats-outcomes"
        desc="실종자 관리 케이스의 담당·처리 현황과 결과 통계를 확인합니다(조회 전용 — 담당 배정·완료 처리는 실종자 관리 페이지에서 합니다)."
      />

      <StatsFilter
        periodDays={days}
        onPeriodDaysChange={setDays}
        region={region}
        onRegionChange={setRegion}
      />

      {state.error && <div className="stats-error">{state.error}</div>}

      <div className="admin-stat-grid">
        <StatCard
          label="총 케이스"
          value={state.data?.summary.total_cases}
          unit="건"
          loading={state.loading}
        />
        <StatCard
          label="완료"
          value={state.data?.summary.resolved_cases}
          unit="건"
          loading={state.loading}
          className="admin-stat--green"
        />
        <StatCard
          label="해결률"
          value={state.data?.summary.resolution_rate}
          unit="%"
          decimals={1}
          loading={state.loading}
        />
        <StatCard
          label="평균 처리 시간(담당~완료)"
          value={state.data?.summary.average_resolution_hours}
          unit="시간"
          decimals={1}
          loading={state.loading}
          className="admin-stat--amber"
        />
      </div>

      <div className="admin-card admin-table-wrap admin-mb">
        <div className="admin-card-h">지역별 처리 현황</div>
        <table>
          <thead>
            <tr>
              <th>지역</th>
              <th>총 케이스</th>
              <th>완료</th>
              <th>해결률</th>
            </tr>
          </thead>
          <tbody>
            {state.data?.by_region.length ? (
              state.data.by_region.map((row) => (
                <tr key={row.region}>
                  <td>{row.region}</td>
                  <td>{row.total_cases.toLocaleString()}</td>
                  <td>{row.resolved_cases.toLocaleString()}</td>
                  <td>{row.resolution_rate.toFixed(1)}%</td>
                </tr>
              ))
            ) : (
              <TableEmptyRow colSpan={4} />
            )}
          </tbody>
        </table>
      </div>

      <div className="admin-card admin-table-wrap">
        <div className="admin-card-h">
          최근 케이스
          <Link to="/dashboard/cases" className="admin-card-h__link">
            실종자 관리에서 담당·처리하기 →
          </Link>
        </div>
        <table>
          <thead>
            <tr>
              <th style={{ width: 100 }}>SN</th>
              <th style={{ width: 90 }}>이름</th>
              <th style={{ width: 60 }}>성별</th>
              <th style={{ width: 50 }}>나이</th>
              <th style={{ width: 110 }}>지역</th>
              <th style={{ width: 70 }}>상태</th>
              <th style={{ width: 90 }}>담당자</th>
              <th style={{ width: 130 }}>담당 시각</th>
              <th style={{ width: 130 }}>완료 시각</th>
            </tr>
          </thead>
          <tbody>
            {state.data?.recent_cases.length ? (
              state.data.recent_cases.map((row) => (
                <tr key={row.id}>
                  <td>{row.sn}</td>
                  <td>{row.missing_name ?? '-'}</td>
                  <td>
                    {row.gender === 'M'
                      ? '남'
                      : row.gender === 'F'
                        ? '여'
                        : '-'}
                  </td>
                  <td>{row.age ?? '-'}</td>
                  <td>{row.missing_location ?? '-'}</td>
                  <td>
                    <span
                      className={`admin-pill ${
                        row.status === '3'
                          ? 'admin-pill--ok'
                          : row.status === '2'
                            ? 'admin-pill--muted'
                            : 'admin-pill--danger'
                      }`}
                    >
                      {{ 1: '대기', 2: '진행중', 3: '완료' }[row.status] ??
                        row.status}
                    </span>
                  </td>
                  <td>{row.assigned_investigator_name ?? '-'}</td>
                  <td>
                    {row.assigned_at ? formatDateTime(row.assigned_at) : '-'}
                  </td>
                  <td>
                    {row.resolved_at ? formatDateTime(row.resolved_at) : '-'}
                  </td>
                </tr>
              ))
            ) : (
              <TableEmptyRow colSpan={9} />
            )}
          </tbody>
        </table>
      </div>
    </>
  );
}

export function StatsExportView() {
  const initialRange = useMemo(() => recentDateRange(90), []);
  const [statType, setStatType] = useState('cctv');
  const [fromDate, setFromDate] = useState(initialRange.fromDate);
  const [toDate, setToDate] = useState(initialRange.toDate);
  const [exporting, setExporting] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);
  const [error, setError] = useState('');
  const [fileFormat, setFileFormat] = useState('csv');

  const logs = useStatsQuery((signal) => fetchExportLogs(signal), [refreshKey]);

  async function handleExport() {
    setExporting(true);
    setError('');

    try {
      await exportStats({
        stat_type: statType,
        from_date: fromDate,
        to_date: toDate,
      });
      setRefreshKey((value) => value + 1);
    } catch (caughtError) {
      setError(
        caughtError instanceof Error
          ? caughtError.message
          : '내보내기에 실패했습니다.',
      );
    } finally {
      setExporting(false);
    }
  }

  return (
    <>
      <PageHead
        viewId="stats-export"
        desc="통계 데이터를 ZIP로 내보내고 이력을 확인합니다."
      />

      <div className="admin-card admin-mb">
        <div className="admin-card-h">내보내기</div>
        <div className="admin-card-b">
          <div className="admin-form-row">
            <div className="admin-fld">
              <label>통계 종류</label>
              <select
                value={statType}
                onChange={(event) => setStatType(event.target.value)}
              >
                <option value="cctv">CCTV 통계</option>
                <option value="search">검색 통계</option>
                <option value="demographic">인구 통계</option>
                <option value="outcomes">처리 결과 통계</option>
              </select>
            </div>

            <div className="admin-fld">
              <label>시작일</label>
              <input
                type="date"
                value={fromDate}
                onChange={(event) => setFromDate(event.target.value)}
              />
            </div>

            <div className="admin-fld">
              <label>종료일</label>
              <input
                type="date"
                value={toDate}
                onChange={(event) => setToDate(event.target.value)}
              />
            </div>

            <div className="admin-fld">
              <label>형식</label>
              <select
                value={fileFormat}
                onChange={(e) => setFileFormat(e.target.value)}
              >
                <option value="csv">CSV</option>
                <option value="png">그래프 PNG</option>
                <option value="zip">CSV + 그래프 ZIP</option>
              </select>
            </div>

            <div className="admin-fld" style={{ flex: '0 0 auto' }}>
              <label>&nbsp;</label>
              <button
                type="button"
                className="admin-btn admin-btn--primary"
                disabled={exporting || !fromDate || !toDate}
                onClick={handleExport}
              >
                {exporting ? '내보내는 중' : '내보내기'}
              </button>
            </div>
          </div>

          {(error || logs.error) && (
            <div className="stats-error">{error ?? logs.error}</div>
          )}
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
              <th>행 수</th>
            </tr>
          </thead>
          <tbody>
            {logs.data?.length ? (
              logs.data.map((row) => (
                <tr key={row.id}>
                  <td>{formatDateTime(row.created_at)}</td>
                  <td>{STAT_TYPE_LABELS[row.stat_type] ?? row.stat_type}</td>
                  <td>
                    {row.from_date} ~ {row.to_date}
                  </td>
                  <td>{row.file_format}</td>
                  <td>{row.requested_by_name}</td>
                  <td>{row.row_count.toLocaleString()}</td>
                </tr>
              ))
            ) : (
              <TableEmptyRow colSpan={6} />
            )}
          </tbody>
        </table>
      </div>
    </>
  );
}
