/** 회원 관리 뷰 — 가입 승인 대기·전체 회원 (/member/admin 연동) */
import { useCallback, useEffect, useMemo, useState } from 'react';
import PageHead from '../components/PageHead';
import { TableEmptyRow } from '../components/EmptyState';
import {
  fetchUsers,
  updateApproval,
  roleLabel,
  statusLabel,
  ROLE_LABELS,
} from '../../../api/client';

const fmtDate = (s) => (s ? new Date(s).toLocaleDateString('ko-KR') : '-');

// ────────────────────────────────────────────────────────────
// 가입 승인 대기
// ────────────────────────────────────────────────────────────
export function MembersPendingView() {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [selected, setSelected] = useState(() => new Set());
  const [keyword, setKeyword] = useState('');
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const data = await fetchUsers('0'); // 0 = 대기
      setRows(data);
      setSelected(new Set());
    } catch (err) {
      setError(
        err?.response?.status === 403
          ? '관리자 권한이 필요합니다.'
          : '목록을 불러오지 못했습니다.',
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const filtered = useMemo(() => {
    const k = keyword.trim().toLowerCase();
    if (!k) return rows;
    return rows.filter((u) =>
      [u.full_name, u.email, u.organization]
        .filter(Boolean)
        .some((v) => v.toLowerCase().includes(k)),
    );
  }, [rows, keyword]);

  const allChecked = filtered.length > 0 && selected.size === filtered.length;

  const toggleAll = () =>
    setSelected(allChecked ? new Set() : new Set(filtered.map((u) => u.id)));

  const toggleOne = (id) =>
    setSelected((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });

  // 승인: 각 사용자의 신청 역할(requested_role)로 승인
  const approveSelected = async () => {
    if (selected.size === 0) return;
    setBusy(true);
    try {
      await Promise.all(
        [...selected].map(
          (id) => updateApproval(id, { status: '1' }), // role 미지정 → 서버가 requested_role 사용
        ),
      );
      await load();
    } catch {
      setError('승인 처리 중 오류가 발생했습니다.');
    } finally {
      setBusy(false);
    }
  };

  const rejectSelected = async () => {
    if (selected.size === 0) return;
    const reason = window.prompt('반려 사유를 입력하세요 (선택):', '') ?? '';
    setBusy(true);
    try {
      await Promise.all(
        [...selected].map((id) =>
          updateApproval(id, {
            status: '2',
            rejection_reason: reason || undefined,
          }),
        ),
      );
      await load();
    } catch {
      setError('반려 처리 중 오류가 발생했습니다.');
    } finally {
      setBusy(false);
    }
  };

  // 개별 승인 시 역할을 바꿔서 승인하고 싶을 때
  const approveOneWithRole = async (id, roleCode) => {
    setBusy(true);
    try {
      await updateApproval(id, { status: '1', role: roleCode });
      await load();
    } catch {
      setError('승인 처리 중 오류가 발생했습니다.');
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <PageHead
        viewId="members-pending"
        desc="가입을 신청한 사용자를 검토하고 승인하거나 반려합니다. 승인 시 역할을 함께 지정하세요."
      />
      <div className="admin-toolbar">
        <input
          placeholder="이름·이메일·소속 검색"
          value={keyword}
          onChange={(e) => setKeyword(e.target.value)}
        />
        <div className="admin-spacer" />
        <button
          type="button"
          className="admin-btn"
          onClick={rejectSelected}
          disabled={busy || selected.size === 0}
        >
          선택 반려
        </button>
        <button
          type="button"
          className="admin-btn admin-btn--primary"
          onClick={approveSelected}
          disabled={busy || selected.size === 0}
        >
          선택 승인{selected.size > 0 ? ` (${selected.size})` : ''}
        </button>
      </div>
      <div className="admin-card admin-table-wrap">
        <table>
          <thead>
            <tr>
              <th style={{ width: 34 }}>
                <input
                  type="checkbox"
                  aria-label="전체 선택"
                  checked={allChecked}
                  onChange={toggleAll}
                  disabled={filtered.length === 0}
                />
              </th>
              <th>이름</th>
              <th>이메일</th>
              <th>소속</th>
              <th>신청 역할</th>
              <th>신청일</th>
              <th style={{ textAlign: 'right' }}>처리</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <TableEmptyRow colSpan={7} message="불러오는 중…" />
            ) : error ? (
              <TableEmptyRow colSpan={7} message={error} />
            ) : filtered.length === 0 ? (
              <TableEmptyRow
                colSpan={7}
                message="승인 대기 중인 신청이 없습니다."
              />
            ) : (
              filtered.map((u) => (
                <tr key={u.id}>
                  <td>
                    <input
                      type="checkbox"
                      aria-label={`${u.full_name} 선택`}
                      checked={selected.has(u.id)}
                      onChange={() => toggleOne(u.id)}
                    />
                  </td>
                  <td>{u.full_name}</td>
                  <td>{u.email}</td>
                  <td>{u.organization}</td>
                  <td>
                    <select
                      defaultValue={u.requested_role}
                      onChange={(e) => approveOneWithRole(u.id, e.target.value)}
                      disabled={busy}
                      title="역할을 선택하면 해당 역할로 즉시 승인됩니다"
                    >
                      {Object.entries(ROLE_LABELS).map(([code, label]) => (
                        <option key={code} value={code}>
                          {label}
                        </option>
                      ))}
                    </select>
                  </td>
                  <td>{fmtDate(u.created_at)}</td>
                  <td style={{ textAlign: 'right' }}>
                    <button
                      type="button"
                      className="admin-btn admin-btn--primary"
                      onClick={() => approveOneWithRole(u.id, u.requested_role)}
                      disabled={busy}
                    >
                      승인
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </>
  );
}

// ────────────────────────────────────────────────────────────
// 전체 회원
// ────────────────────────────────────────────────────────────
export function MembersAllView() {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [keyword, setKeyword] = useState('');
  const [statusFilter, setStatusFilter] = useState(''); // '' = 전체
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const data = await fetchUsers(statusFilter || undefined);
      setRows(data);
    } catch (err) {
      setError(
        err?.response?.status === 403
          ? '관리자 권한이 필요합니다.'
          : '목록을 불러오지 못했습니다.',
      );
    } finally {
      setLoading(false);
    }
  }, [statusFilter]);

  useEffect(() => {
    load();
  }, [load]);

  const filtered = useMemo(() => {
    const k = keyword.trim().toLowerCase();
    if (!k) return rows;
    return rows.filter((u) =>
      [u.full_name, u.email]
        .filter(Boolean)
        .some((v) => v.toLowerCase().includes(k)),
    );
  }, [rows, keyword]);

  const suspend = async (id) => {
    const reason = window.prompt('정지 사유를 입력하세요 (선택):', '') ?? '';
    setBusy(true);
    try {
      await updateApproval(id, {
        status: '3',
        rejection_reason: reason || undefined,
      });
      await load();
    } catch {
      setError('정지 처리 중 오류가 발생했습니다.');
    } finally {
      setBusy(false);
    }
  };

  // 정지·반려된 계정을 다시 승인(복구). 백엔드가 APPROVED 전환을 허용.
  const reactivate = async (u) => {
    const label = u.approval_status === '3' ? '정지 해제' : '재승인';
    if (!window.confirm(`${u.full_name} 님의 계정을 ${label}할까요?`)) return;
    setBusy(true);
    try {
      await updateApproval(u.id, {
        status: '1',
        role: u.role || u.requested_role,
      });
      await load();
    } catch {
      setError('처리 중 오류가 발생했습니다.');
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <PageHead
        viewId="members-all"
        desc="전체 회원을 조회하고 역할·상태를 관리합니다."
      />
      <div className="admin-toolbar">
        <input
          placeholder="이름·이메일 검색"
          value={keyword}
          onChange={(e) => setKeyword(e.target.value)}
        />
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
        >
          <option value="">전체 상태</option>
          <option value="0">대기</option>
          <option value="1">승인</option>
          <option value="2">반려</option>
          <option value="3">정지</option>
        </select>
        <div className="admin-spacer" />
      </div>
      <div className="admin-card admin-table-wrap">
        <table>
          <thead>
            <tr>
              <th>이름</th>
              <th>이메일</th>
              <th>소속</th>
              <th>역할</th>
              <th>상태</th>
              <th>가입일</th>
              <th style={{ textAlign: 'right' }}>관리</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <TableEmptyRow colSpan={7} message="불러오는 중…" />
            ) : error ? (
              <TableEmptyRow colSpan={7} message={error} />
            ) : filtered.length === 0 ? (
              <TableEmptyRow colSpan={7} message="회원이 없습니다." />
            ) : (
              filtered.map((u) => (
                <tr key={u.id}>
                  <td>{u.full_name}</td>
                  <td>{u.email}</td>
                  <td>{u.organization}</td>
                  <td>{roleLabel(u.role)}</td>
                  <td>{statusLabel(u.approval_status)}</td>
                  <td>{fmtDate(u.created_at)}</td>
                  <td style={{ textAlign: 'right' }}>
                    {u.approval_status === '1' && (
                      <button
                        type="button"
                        className="admin-btn"
                        onClick={() => suspend(u.id)}
                        disabled={busy}
                      >
                        정지
                      </button>
                    )}
                    {(u.approval_status === '2' ||
                      u.approval_status === '3') && (
                      <button
                        type="button"
                        className="admin-btn admin-btn--primary"
                        onClick={() => reactivate(u)}
                        disabled={busy}
                      >
                        {u.approval_status === '3' ? '정지 해제' : '재승인'}
                      </button>
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </>
  );
}
