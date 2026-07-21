/** 실종자 관리 뷰 — 케이스 목록, 담당하기/담당취소/완료처리 */
import { useCallback, useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import PageHead from '../components/PageHead';
import { TableEmptyRow } from '../components/EmptyState';
import {
  assignMissingPersonCase,
  createMissingPersonCase,
  enrichMissingPersonCase,
  fetchMissingPersonCases,
  getRole,
  resolveMissingPersonCase,
  unassignMissingPersonCase,
} from '../../../api/client';

const STATUS_LABELS = { 1: '대기', 2: '진행중', 3: '완료' };

function statusPillClass(status) {
  if (status === '3') return 'admin-pill--ok';
  if (status === '2') return 'admin-pill--muted';
  return 'admin-pill--danger';
}

function fmt(value) {
  return value
    ? new Date(value).toLocaleString('ko-KR', {
        dateStyle: 'short',
        timeStyle: 'short',
      })
    : '-';
}

export function MissingPersonCasesView() {
  const [rows, setRows] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [status, setStatus] = useState('');
  const [assignedToMe, setAssignedToMe] = useState(false);
  const [keyword, setKeyword] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [actionError, setActionError] = useState('');
  const [enrichingId, setEnrichingId] = useState(null);
  const canWrite = getRole() !== '3'; // 3 = 공무원(조회 전용)
  const navigate = useNavigate();

  const PER_PAGE = 20;

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const params = { page, per_page: PER_PAGE };
      if (status) params.status = status;
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
    } finally {
      setLoading(false);
    }
  }, [page, status, assignedToMe, keyword]);

  useEffect(() => {
    load();
  }, [load]);

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
    <>
      <PageHead
        viewId="missing-person-cases"
        desc="안내문자·챗봇 상담으로 등록된 실종자 케이스를 담당·처리합니다. 안내문자는 수집될 때 자동으로 케이스가 생성됩니다."
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
        <label
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 6,
            fontSize: 13,
          }}
        >
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
        <div className="admin-spacer" />
        {canWrite && (
          <button
            type="button"
            className="admin-btn"
            onClick={() => navigate('/admin/missing-person-case-new')}
          >
            새 케이스 등록
          </button>
        )}
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
              <th style={{ width: 90 }}>담당자</th>
              <th style={{ width: 130 }}>담당 시각</th>
              <th style={{ width: 280 }} />
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
                  <td>
                    {row.gender === 'M'
                      ? '남'
                      : row.gender === 'F'
                        ? '여'
                        : '-'}
                  </td>
                  <td>{row.age ?? '-'}</td>
                  <td title={row.clothing ?? undefined}>
                    {row.clothing ?? '-'}
                  </td>
                  <td>{row.missing_location ?? '-'}</td>
                  <td>
                    <span
                      className={`admin-pill ${statusPillClass(row.status)}`}
                    >
                      {STATUS_LABELS[row.status] ?? row.status}
                    </span>
                  </td>
                  <td>{row.assigned_investigator_name ?? '-'}</td>
                  <td>{fmt(row.assigned_at)}</td>
                  <td>
                    {!canWrite ? (
                      <span className="admin-cell-sub">조회만 가능</span>
                    ) : (
                      <>
                        {row.msg_cn && !row.missing_name && (
                          <>
                            <button
                              type="button"
                              className="admin-btn admin-btn--sm"
                              disabled={enrichingId === row.id}
                              onClick={() => handleEnrich(row.id)}
                            >
                              {enrichingId === row.id
                                ? 'AI 채우는 중…'
                                : 'AI로 채우기'}
                            </button>{' '}
                          </>
                        )}
                        {row.status === '1' && (
                          <button
                            type="button"
                            className="admin-btn admin-btn--sm admin-btn--primary"
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
                              className="admin-btn admin-btn--sm"
                              onClick={() =>
                                runAction(unassignMissingPersonCase, row.id)
                              }
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
                        {row.status === '3' && (
                          <span className="admin-cell-sub">처리 완료됨</span>
                        )}
                      </>
                    )}
                  </td>
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
        ※ <code>missing_person_case</code> 테이블 기록입니다. 안내문자는 수집 시
        자동으로 케이스가 생성되고(대기 상태), 담당하기를 누르면 진행중으로,
        완료 처리는 되돌릴 수 없습니다.
      </p>
    </>
  );
}

/** 새 케이스 등록 폼 — 개별 입력, 또는 챗봇에서 넘어올 때 쿼리스트링으로 값 미리 채움
 * (예: /admin/missing-person-case-new?missing_name=...&gender=M&age=30&clothing=...&missing_location=...).
 * 등록자가 자동으로 담당수사관이 되고, 상태는 바로 진행중으로 시작한다(백엔드 처리). */
export function MissingPersonCaseCreateView() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  const [missingName, setMissingName] = useState(
    searchParams.get('missing_name') ?? '',
  );
  const [gender, setGender] = useState(searchParams.get('gender') ?? '');
  const [age, setAge] = useState(searchParams.get('age') ?? '');
  const [clothing, setClothing] = useState(searchParams.get('clothing') ?? '');
  const [missingLocation, setMissingLocation] = useState(
    searchParams.get('missing_location') ?? '',
  );
  const [notes, setNotes] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  const canWrite = getRole() !== '3';

  async function handleSubmit(e) {
    e.preventDefault();
    setSubmitting(true);
    setError('');
    try {
      const created = await createMissingPersonCase({
        missing_name: missingName || null,
        gender: gender || null,
        age: age ? Number(age) : null,
        clothing: clothing || null,
        missing_location: missingLocation || null,
        notes: notes || null,
      });
      navigate(`/admin/missing-person-cases?highlight=${created.id}`);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : '케이스 등록에 실패했습니다.',
      );
    } finally {
      setSubmitting(false);
    }
  }

  if (!canWrite) {
    return (
      <>
        <PageHead
          viewId="missing-person-case-new"
          desc="새 실종자 케이스를 등록합니다."
        />
        <p className="admin-inline-error">
          공무원 계정은 케이스를 등록할 수 없습니다(조회 전용).
        </p>
      </>
    );
  }

  return (
    <>
      <PageHead
        viewId="missing-person-case-new"
        desc="안내문자에 안 묶인 실종자 케이스를 직접 등록합니다. 등록하면 바로 본인이 담당자로 배정됩니다."
      />

      <form className="admin-card" onSubmit={handleSubmit}>
        <div className="admin-card-b">
          <div className="admin-form-row">
            <div className="admin-fld">
              <label>이름</label>
              <input
                value={missingName}
                onChange={(e) => setMissingName(e.target.value)}
              />
            </div>
            <div className="admin-fld">
              <label>성별</label>
              <select
                value={gender}
                onChange={(e) => setGender(e.target.value)}
              >
                <option value="">선택 안 함</option>
                <option value="M">남</option>
                <option value="F">여</option>
              </select>
            </div>
            <div className="admin-fld">
              <label>나이</label>
              <input
                type="number"
                min={0}
                max={150}
                value={age}
                onChange={(e) => setAge(e.target.value)}
              />
            </div>
            <div className="admin-fld">
              <label>지역</label>
              <input
                value={missingLocation}
                onChange={(e) => setMissingLocation(e.target.value)}
                placeholder="예: 서울 관악구"
              />
            </div>
          </div>
          <div className="admin-form-row">
            <div className="admin-fld" style={{ flex: '1 1 100%' }}>
              <label>인상착의</label>
              <input
                value={clothing}
                onChange={(e) => setClothing(e.target.value)}
              />
            </div>
          </div>
          <div className="admin-form-row">
            <div className="admin-fld" style={{ flex: '1 1 100%' }}>
              <label>메모</label>
              <textarea
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                rows={3}
              />
            </div>
          </div>
          {error && <p className="admin-modal__error">{error}</p>}
          <button
            type="submit"
            className="admin-btn admin-btn--primary"
            disabled={submitting}
          >
            {submitting ? '등록 중…' : '케이스 등록'}
          </button>{' '}
          <button
            type="button"
            className="admin-btn"
            onClick={() => navigate('/admin/missing-person-cases')}
          >
            취소
          </button>
        </div>
      </form>
    </>
  );
}
