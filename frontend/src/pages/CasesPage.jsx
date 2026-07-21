/**
 * 실종자 관리 — 케이스 목록, 담당하기/담당취소/완료처리.
 *
 * SearchHistory.jsx와 동일한 구조·클래스 네이밍 패턴을 따른다(헤더 + 요약
 * 카드 + 툴바 + 표) — 프로젝트 고유 디자인 언어에 맞추기 위해 auth-* 재사용
 * 대신 이 페이지 전용 스타일(CasesPage.css)로 새로 만들었다.
 *
 * /admin/*(관리자 콘솔)이 아니라 /dashboard/cases에 둔다 — RequireAdmin은
 * role==관리자만 통과시키는데, 이 페이지는 수사관도 써야 해서 RequireAuth
 * (로그인만 확인) 아래에 둔다.
 */
import { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  assignMissingPersonCase,
  enrichMissingPersonCase,
  fetchMissingPersonCases,
  getRole,
  resolveMissingPersonCase,
  unassignMissingPersonCase,
} from '../api/client';
import './CasesPage.css';

const STATUS_LABELS = { 1: '대기', 2: '진행중', 3: '완료' };
const STATUS_BADGE_MODIFIER = { 1: 'pending', 2: 'progress', 3: 'done' };
const PER_PAGE = 20;

function fmt(value) {
  if (!value) return '-';
  return new Date(value).toLocaleString('ko-KR', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function genderLabel(g) {
  if (g === 'M') return '남';
  if (g === 'F') return '여';
  return '-';
}

export default function CasesPage() {
  const navigate = useNavigate();
  const canWrite = getRole() !== '3'; // 3: 공무원(조회 전용)
  const isInvestigator = getRole() === '2'; // 수사관 — 항상 자기 담당 건만 조회(백엔드가 강제)

  const [rows, setRows] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [status, setStatus] = useState('all');
  const [assignedToMe, setAssignedToMe] = useState(false);
  const [keyword, setKeyword] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [actionError, setActionError] = useState('');
  const [enrichingId, setEnrichingId] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const params = { page, per_page: PER_PAGE };
      if (status !== 'all') params.status = status;
      if (assignedToMe) params.assigned_to_me = true;
      if (keyword.trim()) params.keyword = keyword.trim();
      const data = await fetchMissingPersonCases(params);
      setRows(data.items ?? []);
      setTotal(data.total ?? 0);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : '케이스 목록을 불러오지 못했습니다.',
      );
      setRows([]);
    } finally {
      setLoading(false);
    }
  }, [page, status, assignedToMe, keyword]);

  useEffect(() => {
    load();
  }, [load]);

  const totalPages = Math.max(1, Math.ceil(total / PER_PAGE));
  const pendingCount = rows.filter((r) => r.status === '1').length;
  const inProgressCount = rows.filter((r) => r.status === '2').length;

  const onSearch = (e) => {
    e?.preventDefault();
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
      setActionError(
        err instanceof Error ? err.message : '처리에 실패했습니다.',
      );
    }
  }

  async function handleEnrich(caseId) {
    setActionError('');
    setEnrichingId(caseId);
    try {
      await enrichMissingPersonCase(caseId);
      await load();
    } catch (err) {
      setActionError(
        err instanceof Error ? err.message : 'AI 정보 채우기에 실패했습니다.',
      );
    } finally {
      setEnrichingId(null);
    }
  }

  return (
    <div className="cases-page">
      <header className="cases-page__header">
        <h1>실종자 관리</h1>
        <span className="cases-page__count">
          {loading ? '불러오는 중…' : `총 ${total}건`}
        </span>
        {canWrite && (
          <button
            type="button"
            className="cases-page__new-btn"
            onClick={() => navigate('/dashboard/cases/new')}
          >
            + 새 케이스 등록
          </button>
        )}
        <button
          type="button"
          className="cases-page__refresh"
          onClick={load}
          disabled={loading}
        >
          새로고침
        </button>
      </header>

      <div className="cases-page__panel">
        <div className="cases-page__summary">
          <div className="cases-page__stat-card">
            <span className="cases-page__stat-label">전체 케이스</span>
            <strong>{total}</strong>
          </div>
          <div className="cases-page__stat-card">
            <span className="cases-page__stat-label">이 페이지 · 대기</span>
            <strong>{pendingCount}</strong>
          </div>
          <div className="cases-page__stat-card">
            <span className="cases-page__stat-label">이 페이지 · 진행중</span>
            <strong>{inProgressCount}</strong>
          </div>
        </div>

        <form className="cases-page__toolbar" onSubmit={onSearch}>
          <input
            type="search"
            className="cases-page__search"
            placeholder="이름·지역·SN 검색"
            value={keyword}
            onChange={(e) => setKeyword(e.target.value)}
            aria-label="케이스 검색"
          />

          <div
            className="cases-page__status-tabs"
            role="tablist"
            aria-label="상태 필터"
          >
            {[
              { id: 'all', label: '전체' },
              { id: '1', label: '대기' },
              { id: '2', label: '진행중' },
              { id: '3', label: '완료' },
            ].map((tab) => (
              <button
                key={tab.id}
                type="button"
                role="tab"
                aria-selected={status === tab.id}
                className={`cases-page__status-btn${
                  status === tab.id ? ' cases-page__status-btn--on' : ''
                }`}
                onClick={() => {
                  setStatus(tab.id);
                  setPage(1);
                }}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {isInvestigator ? (
            <span className="cases-page__scope-note">
              내 담당 케이스만 표시됩니다
            </span>
          ) : (
            <label className="cases-page__checkbox">
              <input
                type="checkbox"
                checked={assignedToMe}
                onChange={(e) => {
                  setAssignedToMe(e.target.checked);
                  setPage(1);
                }}
              />
              내 담당만
            </label>
          )}
        </form>

        {error && <p className="cases-page__error">{error}</p>}
        {actionError && <p className="cases-page__error">{actionError}</p>}

        <div className="cases-page__body">
          {!loading && !error && rows.length === 0 && (
            <div className="cases-page__empty">
              <p>등록된 케이스가 없습니다.</p>
              <p>안내문자가 수집되면 자동으로 케이스가 생성됩니다.</p>
            </div>
          )}

          {!error && rows.length > 0 && (
            <div className="cases-page__table-wrap">
              <table className="cases-page__table">
                <thead>
                  <tr>
                    <th scope="col">SN</th>
                    <th scope="col">이름</th>
                    <th scope="col">성별</th>
                    <th scope="col">나이</th>
                    <th scope="col">인상착의</th>
                    <th scope="col">지역</th>
                    <th scope="col">상태</th>
                    <th scope="col">담당자</th>
                    <th scope="col">담당 시각</th>
                    <th scope="col" className="cases-page__col-action">
                      처리
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((row) => (
                    <tr key={row.id}>
                      <td>{row.sn}</td>
                      <td>{row.missing_name ?? '-'}</td>
                      <td>{genderLabel(row.gender)}</td>
                      <td>{row.age ?? '-'}</td>
                      <td title={row.clothing ?? undefined}>
                        {row.clothing ?? '-'}
                      </td>
                      <td>{row.missing_location ?? '-'}</td>
                      <td>
                        <span
                          className={`cases-page__badge cases-page__badge--${STATUS_BADGE_MODIFIER[row.status]}`}
                        >
                          {STATUS_LABELS[row.status] ?? row.status}
                        </span>
                      </td>
                      <td>{row.assigned_investigator_name ?? '-'}</td>
                      <td>{fmt(row.assigned_at)}</td>
                      <td className="cases-page__col-action">
                        {!canWrite ? (
                          <span className="cases-page__readonly">
                            조회만 가능
                          </span>
                        ) : (
                          <div className="cases-page__actions">
                            {row.msg_cn && !row.missing_name && (
                              <button
                                type="button"
                                className="cases-page__action-btn"
                                disabled={enrichingId === row.id}
                                onClick={() => handleEnrich(row.id)}
                              >
                                {enrichingId === row.id
                                  ? 'AI 채우는 중…'
                                  : 'AI로 채우기'}
                              </button>
                            )}
                            {row.status === '1' && (
                              <button
                                type="button"
                                className="cases-page__action-btn cases-page__action-btn--primary"
                                onClick={() =>
                                  runAction(assignMissingPersonCase, row.id)
                                }
                              >
                                담당하기
                              </button>
                            )}
                            {row.status === '2' && (
                              <>
                                <button
                                  type="button"
                                  className="cases-page__action-btn"
                                  onClick={() =>
                                    runAction(unassignMissingPersonCase, row.id)
                                  }
                                >
                                  담당 취소
                                </button>
                                <button
                                  type="button"
                                  className="cases-page__action-btn cases-page__action-btn--primary"
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
                            {row.status === '3' && (
                              <span className="cases-page__readonly">
                                처리 완료됨
                              </span>
                            )}
                          </div>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {total > 0 && (
          <div className="cases-page__pagination">
            <button
              type="button"
              className="cases-page__page-btn"
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page <= 1 || loading}
            >
              이전
            </button>
            <span className="cases-page__page-label">
              {page} / {totalPages}
            </span>
            <button
              type="button"
              className="cases-page__page-btn"
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page >= totalPages || loading}
            >
              다음
            </button>
          </div>
        )}
      </div>

      <p className="cases-page__footnote">
        안내문자는 수집 시 자동으로 케이스가 생성됩니다(대기 상태). 담당하기를
        누르면 진행중으로 넘어가고, 완료 처리는 되돌릴 수 없습니다.
      </p>
    </div>
  );
}
