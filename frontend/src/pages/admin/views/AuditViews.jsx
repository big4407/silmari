/** 감사 로그 뷰 — 로그인 이력·관리자 행동 이력·승인 이력 (전부 연동) */
import { useCallback, useEffect, useState } from 'react';
import PageHead from '../components/PageHead';
import { StatValue, TableEmptyRow } from '../components/EmptyState';
import Pagination from '../components/Pagination';
import { adminPinnedPaginationStyle } from '../components/adminTableUtils';
import {
  fetchLoginHistory,
  LOGIN_FAIL_LABELS,
  fetchAdminHistory,
  ADMIN_ACTION_LABELS,
  ADMIN_TARGET_TYPE_LABELS,
} from '../../../api/client';

export function AuditAdminView() {
  const [rows, setRows] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [keyword, setKeyword] = useState('');
  const [actionFilter, setActionFilter] = useState(''); // '' 전체 / '1'~'6'
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const PER_PAGE = 15; // 관리자 활동 이력 — 요청대로 15줄

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const params = { page, per_page: PER_PAGE };
      if (keyword.trim()) params.actor = keyword.trim();
      if (actionFilter) params.action_type = actionFilter;
      if (startDate) params.start_date = startDate;
      if (endDate) params.end_date = endDate;
      const data = await fetchAdminHistory(params);
      setRows(data.items ?? []);
      setTotal(data.total ?? 0);
    } catch (err) {
      setError(
        err?.response?.status === 403
          ? '관리자 권한이 필요합니다.'
          : '관리자 행동 이력을 불러오지 못했습니다.',
      );
    } finally {
      setLoading(false);
    }
  }, [page, keyword, actionFilter, startDate, endDate]);

  useEffect(() => {
    load();
  }, [load]);

  const totalPages = Math.max(1, Math.ceil(total / PER_PAGE));
  const fmt = (s) =>
    s
      ? new Date(s).toLocaleString('ko-KR', {
          dateStyle: 'short',
          timeStyle: 'medium',
        })
      : '-';

  // detail JSON → 대상·변경 내용 요약 (행동 유형별로 detail 모양이 다를 수 있음)
  const targetSummary = (r) => {
    const d = r.detail ?? {};
    const name = d.target_name ?? d.target_username ?? r.target_id ?? '-';
    if (d.before && d.after) {
      const changed = Object.keys(d.after).filter(
        (k) => d.before[k] !== d.after[k],
      );
      if (changed.length) {
        return `${name} (${changed.map((k) => `${k}: ${d.before[k] ?? '-'} → ${d.after[k] ?? '-'}`).join(', ')})`;
      }
    }
    return name;
  };

  const onSearch = () => {
    setPage(1);
    load();
  };

  return (
    <>
      <PageHead
        viewId="audit-admin"
        desc="관리자가 수행한 모든 작업(데이터 수정·삭제·보내기 등)을 시간순으로 기록합니다. 행위자·대상·결과를 추적할 수 있습니다."
      />
      <div className="admin-toolbar">
        <input
          placeholder="행위자 검색"
          value={keyword}
          onChange={(e) => setKeyword(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && onSearch()}
        />
        <select
          value={actionFilter}
          onChange={(e) => setActionFilter(e.target.value)}
        >
          <option value="">전체 유형</option>
          {Object.entries(ADMIN_ACTION_LABELS).map(([code, label]) => (
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
      <div style={adminPinnedPaginationStyle(PER_PAGE)}>
        <div className="admin-card admin-table-wrap">
        <table>
          <thead>
            <tr>
              <th>시각</th>
              <th>행위자</th>
              <th>유형</th>
              <th>화면</th>
              <th>대상 · 변경 내용</th>
              <th>결과</th>
              <th>IP</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <TableEmptyRow colSpan={7} message="불러오는 중…" />
            ) : error ? (
              <TableEmptyRow colSpan={7} message={error} />
            ) : rows.length === 0 ? (
              <TableEmptyRow
                colSpan={7}
                message="관리자 행동 이력이 없습니다."
              />
            ) : (
              rows.map((r) => (
                <tr key={r.id}>
                  <td>{fmt(r.created_at)}</td>
                  <td>{r.actor_name ?? r.actor_id}</td>
                  <td>
                    <span className="admin-pill admin-pill--muted">
                      {ADMIN_ACTION_LABELS[r.action_type] ?? r.action_type}
                    </span>
                  </td>
                  <td>
                    {ADMIN_TARGET_TYPE_LABELS[r.target_type] ?? r.target_type}
                  </td>
                  <td title={targetSummary(r)}>{targetSummary(r)}</td>
                  <td>
                    <span
                      className={`admin-pill ${
                        r.success ? 'admin-pill--ok' : 'admin-pill--danger'
                      }`}
                    >
                      {r.success ? '성공' : '실패'}
                    </span>
                  </td>
                  <td>{r.ip_address ?? '-'}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <Pagination
        page={page}
        totalPages={totalPages}
        total={total}
        onPageChange={setPage}
        loading={loading}
      />
      </div>

      <p className="admin-footnote">
        ※ <code>admin_history</code> 테이블 기록입니다. 가입 승인·권한 변경은
        보안 감사를 위해 <b>승인·권한변경 이력</b>에서 별도로도 볼 수 있습니다.
      </p>
    </>
  );
}

export function AuditApprovalView() {
  const [rows, setRows] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [keyword, setKeyword] = useState('');
  const [actionFilter, setActionFilter] = useState(''); // '' 전체 / '1'~'4'
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const PER_PAGE = 15; // 승인·권한변경 이력 — 요청대로 15줄

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const params = { page, per_page: PER_PAGE, approval_only: true };
      if (keyword.trim()) params.actor = keyword.trim();
      if (actionFilter) params.action_type = actionFilter;
      const data = await fetchAdminHistory(params);
      setRows(data.items ?? []);
      setTotal(data.total ?? 0);
    } catch (err) {
      setError(
        err?.response?.status === 403
          ? '관리자 권한이 필요합니다.'
          : '승인·권한 변경 이력을 불러오지 못했습니다.',
      );
    } finally {
      setLoading(false);
    }
  }, [page, keyword, actionFilter]);

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

  // detail JSON → "역할 미지정 → 수사관" 식 변경 요약
  const roleLabel = (v) =>
    v == null ? '미지정' : ({ 1: '관리자', 2: '수사관', 3: '공무원' }[v] ?? v);
  const changeSummary = (d) => {
    if (!d) return '-';
    const b = d.before ?? {};
    const a = d.after ?? {};
    const parts = [];
    if (b.role !== a.role) {
      parts.push(`역할 ${roleLabel(b.role)} → ${roleLabel(a.role)}`);
    }
    return parts.length ? parts.join(', ') : '상태 변경';
  };
  const onSearch = () => {
    setPage(1);
    load();
  };

  return (
    <>
      <PageHead
        viewId="audit-approval"
        desc="가입 승인과 역할(권한) 변경을 별도로 추적합니다. 누가 누구에게 어떤 권한을 부여했는지가 보안 감사의 핵심입니다."
      />
      <div className="admin-toolbar">
        <input
          placeholder="처리자 검색"
          value={keyword}
          onChange={(e) => setKeyword(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && onSearch()}
        />
        <select
          value={actionFilter}
          onChange={(e) => setActionFilter(e.target.value)}
        >
          <option value="">전체 유형</option>
          <option value="1">승인</option>
          <option value="2">반려</option>
          <option value="3">정지</option>
          <option value="4">재승인</option>
        </select>
        <button type="button" className="admin-btn" onClick={onSearch}>
          검색
        </button>
      </div>
      <div style={adminPinnedPaginationStyle(PER_PAGE)}>
        <div className="admin-card admin-table-wrap">
        <table>
          <thead>
            <tr>
              <th>시각</th>
              <th>처리자</th>
              <th>유형</th>
              <th>대상</th>
              <th>변경 (전 → 후)</th>
              <th>사유</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <TableEmptyRow colSpan={6} message="불러오는 중…" />
            ) : error ? (
              <TableEmptyRow colSpan={6} message={error} />
            ) : rows.length === 0 ? (
              <TableEmptyRow
                colSpan={6}
                message="승인·권한 변경 이력이 없습니다."
              />
            ) : (
              rows.map((r) => {
                const d = r.detail ?? {};
                return (
                  <tr key={r.id}>
                    <td>{fmt(r.created_at)}</td>
                    <td>{r.actor_name ?? r.actor_id}</td>
                    <td>
                      <span className="admin-pill admin-pill--muted">
                        {ADMIN_ACTION_LABELS[r.action_type] ?? r.action_type}
                      </span>
                    </td>
                    <td>
                      {d.target_name ?? d.target_username ?? r.target_id ?? '-'}
                    </td>
                    <td>{changeSummary(d)}</td>
                    <td>{d.reason ?? '-'}</td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      <Pagination
        page={page}
        totalPages={totalPages}
        total={total}
        onPageChange={setPage}
        loading={loading}
      />
      </div>

      <p className="admin-footnote">
        ※ 승인·반려·정지·재승인이 <code>admin_history</code> 에 기록됩니다. 변경
        전후 역할과 사유가 함께 저장되어 권한 부여 경위를 추적할 수 있습니다.
      </p>
    </>
  );
}

export function AuditLoginView() {
  const [rows, setRows] = useState([]);
  const [total, setTotal] = useState(0);
  const [todaySuccess, setTodaySuccess] = useState(0);
  const [todayFailed, setTodayFailed] = useState(0);
  const [page, setPage] = useState(1);
  const [keyword, setKeyword] = useState('');
  const [successFilter, setSuccessFilter] = useState(''); // '' 전체 / 'true' / 'false'
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const PER_PAGE = 10; // 로그인·접근 이력 — 요청대로 10줄

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const params = { page, per_page: PER_PAGE };
      if (keyword.trim()) params.username = keyword.trim();
      if (successFilter !== '') params.success = successFilter;
      const data = await fetchLoginHistory(params);
      setRows(data.items ?? []);
      setTotal(data.total ?? 0);
      setTodaySuccess(data.today_success ?? 0);
      setTodayFailed(data.today_failed ?? 0);
    } catch (err) {
      setError(
        err?.response?.status === 403
          ? '관리자 권한이 필요합니다.'
          : '로그인 이력을 불러오지 못했습니다.',
      );
    } finally {
      setLoading(false);
    }
  }, [page, keyword, successFilter]);

  useEffect(() => {
    load();
  }, [load]);

  const totalPages = Math.max(1, Math.ceil(total / PER_PAGE));
  const fmt = (s) =>
    s
      ? new Date(s).toLocaleString('ko-KR', {
          dateStyle: 'short',
          timeStyle: 'medium',
        })
      : '-';
  const shortUA = (ua) => {
    if (!ua) return '-';
    const m = ua.match(/(Chrome|Firefox|Safari|Edge|Edg)\/[\d.]+/);
    return m ? m[0].replace('Edg', 'Edge') : ua.slice(0, 24);
  };
  const onSearch = () => {
    setPage(1);
    load();
  };

  return (
    <>
      <PageHead
        viewId="audit-login"
        desc="로그인 성공·실패와 접근 기록입니다. 이상 접근(반복 실패·비정상 IP)을 탐지합니다. 활성 세션 관리는 회원 관리에서 처리합니다."
      />
      <div className="admin-stat-grid">
        <div className="admin-stat admin-stat--green">
          <div className="admin-label">오늘 로그인 성공</div>
          <StatValue value={todaySuccess} unit="건" />
        </div>
        <div className="admin-stat admin-stat--amber">
          <div className="admin-label">오늘 실패</div>
          <StatValue value={todayFailed} unit="건" />
        </div>
        <div className="admin-stat">
          <div className="admin-label">전체 이력</div>
          <StatValue value={total} unit="건" />
        </div>
      </div>

      <div className="admin-toolbar">
        <input
          placeholder="계정(아이디) 검색"
          value={keyword}
          onChange={(e) => setKeyword(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && onSearch()}
        />
        <select
          value={successFilter}
          onChange={(e) => setSuccessFilter(e.target.value)}
        >
          <option value="">전체 결과</option>
          <option value="true">성공만</option>
          <option value="false">실패만</option>
        </select>
        <button type="button" className="admin-btn" onClick={onSearch}>
          검색
        </button>
      </div>

      <div style={adminPinnedPaginationStyle(PER_PAGE)}>
        <div className="admin-card admin-table-wrap">
        <table>
          <thead>
            <tr>
              <th>시각</th>
              <th>계정</th>
              <th>결과</th>
              <th>사유</th>
              <th>IP</th>
              <th>기기</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <TableEmptyRow colSpan={6} message="불러오는 중…" />
            ) : error ? (
              <TableEmptyRow colSpan={6} message={error} />
            ) : rows.length === 0 ? (
              <TableEmptyRow colSpan={6} message="로그인 이력이 없습니다." />
            ) : (
              rows.map((r) => (
                <tr key={r.id}>
                  <td>{fmt(r.created_at)}</td>
                  <td>
                    {r.username}
                    {r.full_name ? ` (${r.full_name})` : ''}
                  </td>
                  <td>
                    <span
                      className={`admin-pill ${
                        r.success ? 'admin-pill--ok' : 'admin-pill--danger'
                      }`}
                    >
                      {r.success ? '성공' : '실패'}
                    </span>
                  </td>
                  <td>
                    {r.success
                      ? '-'
                      : (LOGIN_FAIL_LABELS[r.fail_reason] ??
                        r.fail_reason ??
                        '-')}
                  </td>
                  <td>{r.ip_address ?? '-'}</td>
                  <td title={r.user_agent ?? ''}>{shortUA(r.user_agent)}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <Pagination
        page={page}
        totalPages={totalPages}
        total={total}
        onPageChange={setPage}
        loading={loading}
      />
      </div>

      <p className="admin-footnote">
        ※ 로그인 성공·실패가 <code>login_history</code> 에 기록됩니다. 같은
        IP에서 실패가 반복되면 이상 접근일 수 있습니다.
      </p>
    </>
  );
}
