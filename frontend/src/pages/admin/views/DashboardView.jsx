/** 관리자 대시보드 — 시스템 KPI·최근 활동 요약 */
import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import PageHead from '../components/PageHead';
import EmptyState, { StatValue, TableEmptyRow } from '../components/EmptyState';
import {
  fetchAdminDashboardSummary,
  fetchAdminHistory,
  fetchMissingPersonCases,
  ADMIN_ACTION_LABELS,
} from '../../../api/client';

const STATUS_LABELS = { 1: '대기', 2: '진행중', 3: '완료' };

function fmt(value) {
  return value
    ? new Date(value).toLocaleString('ko-KR', {
        dateStyle: 'short',
        timeStyle: 'short',
      })
    : '-';
}

export function DashboardView() {
  const [summary, setSummary] = useState(null);
  const [summaryError, setSummaryError] = useState('');
  const [cases, setCases] = useState([]);
  const [casesLoading, setCasesLoading] = useState(true);
  const [history, setHistory] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(true);

  useEffect(() => {
    fetchAdminDashboardSummary()
      .then(setSummary)
      .catch(() => setSummaryError('요약 정보를 불러오지 못했습니다.'));

    fetchMissingPersonCases({ page: 1, per_page: 5, status: '2' })
      .then((data) => setCases(data.items ?? []))
      .catch(() => setCases([]))
      .finally(() => setCasesLoading(false));

    fetchAdminHistory({ page: 1, per_page: 5 })
      .then((data) => setHistory(data.items ?? []))
      .catch(() => setHistory([]))
      .finally(() => setHistoryLoading(false));
  }, []);

  return (
    <>
      <PageHead
        viewId="dashboard"
        desc="오늘의 운영 현황 요약입니다. 처리 대기 항목과 시스템 상태를 한눈에 확인하세요."
      />

      {summaryError && (
        <div className="admin-inline-error admin-mb">{summaryError}</div>
      )}

      <div className="admin-stat-grid">
        <Link
          to="/admin/members-pending"
          className="admin-stat admin-stat--amber"
        >
          <div className="admin-label">가입 승인 대기</div>
          <StatValue value={summary?.pending_approvals} unit="건" />
        </Link>
        <Link to="/admin/case-assignment" className="admin-stat">
          <div className="admin-label">진행 중 실종 사건</div>
          <StatValue value={summary?.in_progress_cases} unit="건" />
        </Link>
        <Link
          to="/admin/search-requests"
          className="admin-stat admin-stat--green"
        >
          <div className="admin-label">오늘 검색 작업</div>
          <StatValue value={summary?.today_searches} unit="건" />
        </Link>
        <Link to="/admin/llm-usage" className="admin-stat admin-stat--red">
          <div className="admin-label">LLM 오류율 (24h)</div>
          <StatValue value={summary?.llm_error_rate_24h} unit="%" />
        </Link>
      </div>

      <div className="admin-cols">
        <div className="admin-card">
          <div className="admin-card-h">
            진행 중인 실종 사건
            <Link to="/admin/case-assignment" className="admin-card-h__link">
              전체 보기 →
            </Link>
          </div>
          <div className="admin-card-b admin-table-wrap">
            <table>
              <thead>
                <tr>
                  <th>SN</th>
                  <th>이름</th>
                  <th>지역</th>
                  <th>담당자</th>
                  <th>상태</th>
                </tr>
              </thead>
              <tbody>
                {casesLoading ? (
                  <TableEmptyRow colSpan={5} message="불러오는 중…" />
                ) : cases.length === 0 ? (
                  <TableEmptyRow
                    colSpan={5}
                    message="진행 중인 사건이 없습니다."
                  />
                ) : (
                  cases.map((c) => (
                    <tr key={c.id}>
                      <td>{c.sn}</td>
                      <td>{c.missing_name ?? '-'}</td>
                      <td>{c.missing_location ?? '-'}</td>
                      <td>{c.assigned_investigator_name ?? '-'}</td>
                      <td>{STATUS_LABELS[c.status] ?? c.status}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
        <div className="admin-card">
          <div className="admin-card-h">
            최근 관리자 활동
            <Link to="/admin/audit-admin" className="admin-card-h__link">
              전체 보기 →
            </Link>
          </div>
          <div className="admin-card-b">
            {historyLoading ? (
              <EmptyState message="불러오는 중…" />
            ) : history.length === 0 ? (
              <EmptyState message="최근 관리자 활동이 없습니다." />
            ) : (
              <ul className="admin-activity-list">
                {history.map((h) => (
                  <li key={h.id}>
                    <span className="admin-pill admin-pill--muted">
                      {ADMIN_ACTION_LABELS[h.action_type] ?? h.action_type}
                    </span>
                    <span className="admin-activity-list__actor">
                      {h.actor_name ?? h.actor_id}
                    </span>
                    <span className="admin-activity-list__time">
                      {fmt(h.created_at)}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      </div>
    </>
  );
}
