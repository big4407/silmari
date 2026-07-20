/** 검색 운영 뷰 — CCTV 소스(지역별 현황·일자별 이력 연동) · 검색 요청 이력(연동) */
import { useCallback, useEffect, useState } from 'react';
import PageHead from '../components/PageHead';
import { StatValue, TableEmptyRow } from '../components/EmptyState';
import {
  fetchAdminSearchRequests,
  fetchCctvCoverage,
  fetchVideoDailySummary,
  retryVideoIndexJob,
  SEARCH_TYPE_LABELS,
} from '../../../api/client';

export function CctvSourceView() {
  const [tab, setTab] = useState('region');
  const [coverage, setCoverage] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const [days, setDays] = useState([]);
  const [daysLoading, setDaysLoading] = useState(true);
  const [daysError, setDaysError] = useState('');
  const [retryDate, setRetryDate] = useState('');
  const [retrying, setRetrying] = useState(false);
  const [retryMessage, setRetryMessage] = useState('');

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError('');
    fetchCctvCoverage()
      .then((data) => {
        if (!cancelled) setCoverage(data);
      })
      .catch((err) => {
        if (cancelled) return;
        setError(
          err?.response?.status === 403
            ? '관리자 권한이 필요합니다.'
            : 'CCTV 수집 현황을 불러오지 못했습니다.',
        );
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const loadDays = useCallback(async () => {
    setDaysLoading(true);
    setDaysError('');
    try {
      const data = await fetchVideoDailySummary({ page: 1, per_page: 20 });
      setDays(data.items ?? []);
    } catch (err) {
      setDaysError(
        err?.response?.status === 403
          ? '관리자 권한이 필요합니다.'
          : '일자별 영상 현황을 불러오지 못했습니다.',
      );
    } finally {
      setDaysLoading(false);
    }
  }, []);

  useEffect(() => {
    if (tab === 'daily') loadDays();
  }, [tab, loadDays]);

  const handleRetry = async () => {
    if (!retryDate) {
      setRetryMessage('재시도할 날짜를 먼저 선택하세요.');
      return;
    }
    setRetrying(true);
    setRetryMessage('');
    try {
      const result = await retryVideoIndexJob(retryDate);
      setRetryMessage(
        `${result.target_date} 재인덱싱 완료 — 대상 ${result.total}건 중 ` +
          `처리 ${result.processed} · 건너뜀 ${result.skipped} · 실패 ${result.failed}`,
      );
      await loadDays();
    } catch (err) {
      setRetryMessage(
        err?.response?.status === 403
          ? '관리자 권한이 필요합니다.'
          : '재인덱싱 요청에 실패했습니다.',
      );
    } finally {
      setRetrying(false);
    }
  };

  const items = coverage?.items ?? [];
  const summaryData = coverage?.summary;

  const summary = (
    <div className="admin-stat-grid">
      <div className="admin-stat">
        <div className="admin-label">수집 지역</div>
        <StatValue value={summaryData?.collected_region_count} unit="구" />
      </div>
      <div className="admin-stat admin-stat--green">
        <div className="admin-label">영상 파일</div>
        <StatValue value={summaryData?.video_file_count} unit="개" />
      </div>
      <div className="admin-stat admin-stat--amber">
        <div className="admin-label">⚠ 수집 실패·누락</div>
        <StatValue value={summaryData?.missing_region_count} unit="구" />
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
            <th>상태</th>
          </tr>
        </thead>
        <tbody>
          {loading ? (
            <TableEmptyRow colSpan={4} message="불러오는 중…" />
          ) : error ? (
            <TableEmptyRow colSpan={4} message={error} />
          ) : items.length === 0 ? (
            <TableEmptyRow colSpan={4} message="수집된 영상이 없습니다." />
          ) : (
            items.map((item) => (
              <tr key={item.region_code}>
                <td>{item.region_name ?? item.region_code}</td>
                <td>{item.cctv_count}</td>
                <td>{item.video_count}</td>
                <td>
                  <span className="admin-pill admin-pill--ok">
                    {item.status}
                  </span>
                </td>
              </tr>
            ))
          )}
        </tbody>
      </table>
      <p className="admin-footnote">
        ※ 용량·시간대 커버리지는 아직 저장하는 데이터가 없어 표시하지 않습니다.
      </p>
    </div>
  );

  const fmtDateTime = (s) =>
    s
      ? new Date(s).toLocaleString('ko-KR', {
          dateStyle: 'short',
          timeStyle: 'medium',
        })
      : '-';

  const dailyTable = (
    <div className="admin-card admin-table-wrap">
      <div className="admin-card-h">
        일자별 영상 현황{' '}
        <span className="admin-pill admin-pill--muted">
          촬영일자(recorded_at) 기준, Video 테이블 집계
        </span>
      </div>
      <table>
        <thead>
          <tr>
            <th>촬영 일자</th>
            <th>영상 파일</th>
            <th>대상 지역 수</th>
            <th>최초 등록</th>
            <th>최종 등록</th>
          </tr>
        </thead>
        <tbody>
          {daysLoading ? (
            <TableEmptyRow colSpan={5} message="불러오는 중…" />
          ) : daysError ? (
            <TableEmptyRow colSpan={5} message={daysError} />
          ) : days.length === 0 ? (
            <TableEmptyRow colSpan={5} message="등록된 영상이 없습니다." />
          ) : (
            days.map((day) => (
              <tr key={day.target_date}>
                <td>{day.target_date}</td>
                <td>{day.video_count}</td>
                <td>{day.region_count}</td>
                <td>{fmtDateTime(day.first_indexed_at)}</td>
                <td>{fmtDateTime(day.last_indexed_at)}</td>
              </tr>
            ))
          )}
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
        regionTable
      ) : (
        <>
          <div className="admin-toolbar">
            <div className="admin-spacer" />
            <input
              type="date"
              value={retryDate}
              onChange={(e) => setRetryDate(e.target.value)}
              title="재인덱싱할 촬영일자"
            />
            <button
              type="button"
              className="admin-btn"
              onClick={handleRetry}
              disabled={retrying}
            >
              {retrying ? '인덱싱 중…' : '인덱싱 재시도'}
            </button>
          </div>
          {retryMessage && <p className="admin-footnote">{retryMessage}</p>}
          {dailyTable}
          <p className="admin-footnote">
            ※ 별도 작업 기록 테이블 없이 Video 테이블을 촬영일자 기준으로 집계한
            표라, 그 날 시도했지만 전부 실패했거나 건너뛴 영상은 여기 안
            잡힙니다 — 실제로 등록에 성공한 영상만 보입니다. "인덱싱 재시도"는
            YOLO·FashionCLIP 처리라 시간이 걸릴 수 있고, 완료될 때까지 응답을
            기다립니다(결과는 저장되지 않는 1회성 응답).
          </p>
        </>
      )}
    </>
  );
}

export function SearchRequestsView() {
  const [rows, setRows] = useState([]);
  const [summary, setSummary] = useState(null);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [keyword, setKeyword] = useState('');
  const [searchType, setSearchType] = useState('');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const PER_PAGE = 10;

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const params = { page, per_page: PER_PAGE };
      if (keyword.trim()) params.keyword = keyword.trim();
      if (searchType) params.search_type = searchType;
      if (startDate) params.start_date = startDate;
      if (endDate) params.end_date = endDate;
      const data = await fetchAdminSearchRequests(params);
      setRows(data.items ?? []);
      setTotal(data.page_info?.total ?? 0);
      setSummary(data.summary ?? null);
    } catch (err) {
      setError(
        err?.response?.status === 403
          ? '관리자 권한이 필요합니다.'
          : '검색 요청 이력을 불러오지 못했습니다.',
      );
    } finally {
      setLoading(false);
    }
  }, [page, keyword, searchType, startDate, endDate]);

  useEffect(() => {
    load();
  }, [load]);

  const totalPages = Math.max(1, Math.ceil(total / PER_PAGE));
  const fmt = (s) =>
    s
      ? new Date(s).toLocaleString('ko-KR', {
          dateStyle: 'short',
          timeStyle: 'short',
        })
      : '-';

  const onSearch = () => {
    setPage(1);
    load();
  };

  return (
    <>
      <PageHead
        viewId="search-requests"
        desc="전체 사용자가 요청한 검색 쿼리 이력입니다. 안내문자·챗봇·자동검색 유형별로 어떤 조건이 검색됐는지 사후 조회·집계합니다."
      />
      <div className="admin-stat-grid">
        <div className="admin-stat">
          <div className="admin-label">오늘 검색 요청</div>
          <StatValue value={summary?.today_total} unit="건" />
        </div>
        <div className="admin-stat">
          <div className="admin-label">안내문자 파싱 (전체)</div>
          <StatValue value={summary?.total_sms} unit="건" />
        </div>
        <div className="admin-stat">
          <div className="admin-label">챗봇 검색 (전체)</div>
          <StatValue value={summary?.total_chatbot} unit="건" />
        </div>
        <div className="admin-stat">
          <div className="admin-label">자동 검색 (전체)</div>
          <StatValue value={summary?.total_auto} unit="건" />
        </div>
      </div>
      <div className="admin-toolbar">
        <input
          placeholder="이름·인상착의·지역 검색"
          value={keyword}
          onChange={(e) => setKeyword(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && onSearch()}
        />
        <select
          value={searchType}
          onChange={(e) => setSearchType(e.target.value)}
        >
          <option value="">전체 유형</option>
          {Object.entries(SEARCH_TYPE_LABELS).map(([code, label]) => (
            <option key={code} value={code}>
              {label}
            </option>
          ))}
        </select>
        <input
          type="date"
          value={startDate}
          onChange={(e) => setStartDate(e.target.value)}
          title="시작일"
        />
        <input
          type="date"
          value={endDate}
          onChange={(e) => setEndDate(e.target.value)}
          title="종료일"
        />
        <div className="admin-spacer" />
        <button type="button" className="admin-btn" onClick={onSearch}>
          검색
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
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <TableEmptyRow colSpan={8} message="불러오는 중…" />
            ) : error ? (
              <TableEmptyRow colSpan={8} message={error} />
            ) : rows.length === 0 ? (
              <TableEmptyRow colSpan={8} message="검색 요청 이력이 없습니다." />
            ) : (
              rows.map((r) => (
                <tr key={r.id}>
                  <td>{r.id}</td>
                  <td>
                    <span className="admin-pill admin-pill--muted">
                      {SEARCH_TYPE_LABELS[r.search_type] ?? r.search_type}
                    </span>
                  </td>
                  <td>{r.requester_name ?? r.requester_username ?? '-'}</td>
                  <td title={r.message_preview ?? undefined}>
                    {r.message_preview ?? '-'}
                  </td>
                  <td>
                    {r.missing_name ?? '-'}
                    {r.gender ? ` (${r.gender === 'M' ? '남' : '여'}` : ''}
                    {r.age
                      ? `${r.gender ? ', ' : ' ('}${r.age}세)`
                      : r.gender
                        ? ')'
                        : ''}
                  </td>
                  <td title={r.clothing ?? undefined}>{r.clothing ?? '-'}</td>
                  <td>
                    {r.missing_location ?? '-'}
                    {r.missing_time ? ` · ${fmt(r.missing_time)}` : ''}
                  </td>
                  <td>{fmt(r.searched_at)}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {total > 0 && (
        <div
          className="admin-toolbar"
          style={{ justifyContent: 'center', marginTop: 12 }}
        >
          <button
            type="button"
            className="admin-btn"
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page <= 1 || loading}
          >
            이전
          </button>
          <span className="admin-pill admin-pill--muted">
            {page} / {totalPages} (총 {total}건)
          </span>
          <button
            type="button"
            className="admin-btn"
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page >= totalPages || loading}
          >
            다음
          </button>
        </div>
      )}

      <p className="admin-footnote">
        ※ <code>search</code> 테이블의 요청 이력입니다.
      </p>
    </>
  );
}
