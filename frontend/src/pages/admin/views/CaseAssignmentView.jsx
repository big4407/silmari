/** 관리자 콘솔 — 실종사건 관리. 담당자 배정(아무 수사관에게나)/완료처리/담당취소.
 *
 * 메인페이지(/dashboard/cases)는 수사관·관리자 모두 "담당하기"(자기 배정)만
 * 가능하게 단순화했고, 특정 수사관을 골라 배정하는 기능은 관리자 콘솔인
 * 여기로 옮겼다 — 관리자 전용 화면이라 /admin/* 아래 두는 게 자연스럽다.
 */
import { useCallback, useEffect, useState } from 'react';
import PageHead from '../components/PageHead';
import { TableEmptyRow } from '../components/EmptyState';
import {
  assignMissingPersonCase,
  fetchApprovedInvestigators,
  fetchMissingPersonCases,
  resolveMissingPersonCase,
  unassignMissingPersonCase,
} from '../../../api/client';

const STATUS_LABELS = { 1: '대기', 2: '진행중', 3: '완료' };
const PER_PAGE = 20;

function fmt(value) {
  return value
    ? new Date(value).toLocaleString('ko-KR', { dateStyle: 'short', timeStyle: 'short' })
    : '-';
}

function genderLabel(g) {
  if (g === 'M') return '남';
  if (g === 'F') return '여';
  return '-';
}

export function CaseAssignmentView() {
  const [rows, setRows] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [status, setStatus] = useState('');
  const [keyword, setKeyword] = useState('');
  const [investigators, setInvestigators] = useState([]);
  const [assignSelections, setAssignSelections] = useState({}); // { [caseId]: investigatorId }
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [actionError, setActionError] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const params = { page, per_page: PER_PAGE };
      if (status) params.status = status;
      if (keyword.trim()) params.keyword = keyword.trim();
      const data = await fetchMissingPersonCases(params);
      setRows(data.items ?? []);
      setTotal(data.total ?? 0);
    } catch (err) {
      setError(err instanceof Error ? err.message : '케이스 목록을 불러오지 못했습니다.');
      setRows([]);
    } finally {
      setLoading(false);
    }
  }, [page, status, keyword]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    fetchApprovedInvestigators()
      .then((list) => setInvestigators(list ?? []))
      .catch(() => setInvestigators([]));
  }, []);

  const totalPages = Math.max(1, Math.ceil(total / PER_PAGE));

  const onSearch = () => {
    setPage(1);
    load();
  };

  async function runAction(action, caseId, confirmMessage) {
    if (confirmMessage && !window.confirm(confirmMessage)) return;
    setActionError('');
    try {
      await action(caseId);
      await load();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : '처리에 실패했습니다.');
    }
  }

  async function handleAssign(caseId) {
    const investigatorId = assignSelections[caseId];
    if (!investigatorId) return;
    setActionError('');
    try {
      await assignMissingPersonCase(caseId, investigatorId);
      await load();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : '담당 배정에 실패했습니다.');
    }
  }

  return (
    <>
      <PageHead
        viewId="case-assignment"
        desc="실종자 케이스를 수사관에게 배정하고 완료·담당취소 처리합니다. 담당자를 직접 선택해 배정할 수 있습니다(관리자 전용)."
      />

      <div className="admin-toolbar">
        <input
          placeholder="이름·지역·SN 검색"
          value={keyword}
          onChange={(e) => setKeyword(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && onSearch()}
        />
        <select
          value={status}
          onChange={(e) => {
            setStatus(e.target.value);
            setPage(1);
          }}
        >
          <option value="">전체 상태</option>
          {Object.entries(STATUS_LABELS).map(([code, label]) => (
            <option key={code} value={code}>
              {label}
            </option>
          ))}
        </select>
        <div className="admin-spacer" />
        <button type="button" className="admin-btn" onClick={onSearch}>
          검색
        </button>
      </div>

      {actionError && <p className="admin-modal__error">{actionError}</p>}

      <div className="admin-card admin-table-wrap">
        <table>
          <thead>
            <tr>
              <th style={{ width: 100 }}>SN</th>
              <th style={{ width: 90 }}>이름</th>
              <th style={{ width: 60 }}>성별</th>
              <th style={{ width: 50 }}>나이</th>
              <th>인상착의</th>
              <th style={{ width: 110 }}>지역</th>
              <th style={{ width: 70 }}>상태</th>
              <th style={{ width: 100 }}>담당자</th>
              <th style={{ width: 130 }}>담당 시각</th>
              <th style={{ width: 260 }} />
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <TableEmptyRow colSpan={10} message="불러오는 중…" />
            ) : error ? (
              <TableEmptyRow colSpan={10} message={error} />
            ) : rows.length === 0 ? (
              <TableEmptyRow colSpan={10} message="케이스가 없습니다." />
            ) : (
              rows.map((row) => (
                <tr key={row.id}>
                  <td>{row.sn}</td>
                  <td>{row.missing_name ?? '-'}</td>
                  <td>{genderLabel(row.gender)}</td>
                  <td>{row.age ?? '-'}</td>
                  <td title={row.clothing ?? undefined}>{row.clothing ?? '-'}</td>
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
                      {STATUS_LABELS[row.status] ?? row.status}
                    </span>
                  </td>
                  <td>{row.assigned_investigator_name ?? '-'}</td>
                  <td>{fmt(row.assigned_at)}</td>
                  <td>
                    {row.status === '1' && (
                      <div className="admin-form-row" style={{ margin: 0, gap: 6 }}>
                        <select
                          style={{ maxWidth: 140 }}
                          value={assignSelections[row.id] ?? ''}
                          onChange={(e) =>
                            setAssignSelections((prev) => ({
                              ...prev,
                              [row.id]: e.target.value,
                            }))
                          }
                        >
                          <option value="">담당자 선택…</option>
                          {investigators.map((inv) => (
                            <option key={inv.id} value={inv.id}>
                              {inv.full_name} ({inv.username})
                            </option>
                          ))}
                        </select>
                        <button
                          type="button"
                          className="admin-btn admin-btn--sm admin-btn--primary"
                          disabled={!assignSelections[row.id]}
                          onClick={() => handleAssign(row.id)}
                        >
                          배정
                        </button>
                      </div>
                    )}
                    {row.status === '2' && (
                      <>
                        <button
                          type="button"
                          className="admin-btn admin-btn--sm"
                          onClick={() => runAction(unassignMissingPersonCase, row.id)}
                        >
                          담당 취소
                        </button>{' '}
                        <button
                          type="button"
                          className="admin-btn admin-btn--sm admin-btn--primary"
                          onClick={() =>
                            runAction(
                              resolveMissingPersonCase,
                              row.id,
                              '완료 처리하면 되돌릴 수 없습니다. 계속할까요?',
                            )
                          }
                        >
                          완료 처리
                        </button>
                      </>
                    )}
                    {row.status === '3' && <span className="admin-cell-sub">처리 완료됨</span>}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {total > 0 && (
        <div className="admin-toolbar" style={{ justifyContent: 'center', marginTop: 12 }}>
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
        ※ 대기 상태 케이스만 담당자를 배정할 수 있습니다. 완료 처리는 되돌릴 수 없습니다.
      </p>
    </>
  );
}
