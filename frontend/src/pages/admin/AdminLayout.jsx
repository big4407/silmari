/**
 * 관리자 콘솔 레이아웃 — navConfig 기반 사이드바 + 뷰 라우팅.
 *
 * 하위: AdminViewPage (:viewId) — 회원·메시지·검색운영·감사 등
 */
import { useState, useEffect } from 'react';
import { Link, NavLink, Outlet, useLocation } from 'react-router-dom';
import { NAV } from './navConfig';
import { fetchUsers } from '../../api/client';
import useLogout from '../../hooks/useLogout';
import './AdminLayout.css';

export default function AdminLayout() {
  const location = useLocation();

  // 현재 URL(/admin/:viewId)이 속한 그룹 key(node.group)를 찾는다 — 새로고침
  // 하거나 다른 그룹의 메뉴로 이동해도 지금 보고 있는 페이지의 그룹은 항상
  // 펼쳐진 채로 보이게 하기 위함. 없으면 null.
  const activeGroupKey = (() => {
    const viewId = location.pathname.split('/admin/')[1]?.split('/')[0];
    if (!viewId) return null;
    const node = NAV.find(
      (n) => !n.solo && n.items.some((it) => it.id === viewId),
    );
    return node?.group ?? null;
  })();

  const [collapsed, setCollapsed] = useState(() => {
    const initial = Object.fromEntries(
      NAV.map((node, i) => [node.group || node.id, i > 3]),
    );
    // 기본 규칙(4번째 그룹부터 접힘)보다, 지금 보고 있는 페이지의 그룹을
    // 펼쳐두는 게 우선이다.
    if (activeGroupKey) initial[activeGroupKey] = false;
    return initial;
  });

  // 새로고침이 아니라 사이드바 클릭 없이 다른 그룹의 페이지로 SPA 이동한
  // 경우(예: 링크를 통해 들어온 경우)에도 그 그룹이 접혀있으면 펼친다.
  // 사용자가 수동으로 다른 그룹을 접어둔 상태는 건드리지 않는다.
  useEffect(() => {
    if (!activeGroupKey) return;
    setCollapsed((prev) =>
      prev[activeGroupKey] ? { ...prev, [activeGroupKey]: false } : prev,
    );
  }, [activeGroupKey]);

  const { doLogout, loading } = useLogout();
  const [pendingCount, setPendingCount] = useState(0);

  // 가입 승인 대기 건수 — 사이드바 배지용
  useEffect(() => {
    let alive = true;
    const refresh = () => {
      fetchUsers('0')
        .then((users) => {
          if (alive) setPendingCount(Array.isArray(users) ? users.length : 0);
        })
        .catch(() => {
          if (alive) setPendingCount(0);
        });
    };
    refresh(); // 최초 로드

    // 승인/반려로 대기 목록이 바뀌면 배지 갱신
    const onChanged = (e) => {
      const c = e?.detail?.count;
      if (typeof c === 'number') setPendingCount(c);
      else refresh();
    };
    window.addEventListener('members-pending-changed', onChanged);

    return () => {
      alive = false;
      window.removeEventListener('members-pending-changed', onChanged);
    };
  }, []);

  const toggleGroup = (key) => {
    setCollapsed((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  return (
    <div className="admin-console">
      <header className="admin-topbar">
        <div className="admin-brand">
          <Link to="/" className="admin-logo">
            실마리
          </Link>
          <span className="admin-sub">관리자 콘솔</span>
        </div>
        <div className="admin-right">
          <button
            type="button"
            className="admin-logout-btn"
            onClick={doLogout}
            disabled={loading}
          >
            로그아웃
          </button>
        </div>
      </header>

      <div className="admin-layout">
        <aside className="admin-sidebar">
          {NAV.map((node, gi) => {
            if (node.solo) {
              return (
                <NavLink
                  key={node.id}
                  to={`/admin/${node.id}`}
                  className={({ isActive }) =>
                    `admin-nav-solo${isActive ? ' admin-nav-solo--active' : ''}`
                  }
                >
                  <span>▣</span> {node.label}
                </NavLink>
              );
            }

            const isCollapsed = collapsed[node.group] ?? gi > 3;

            return (
              <div
                key={node.group}
                className={`admin-nav-group${isCollapsed ? ' admin-nav-group--collapsed' : ''}`}
              >
                <button
                  type="button"
                  className="admin-nav-head"
                  onClick={() => toggleGroup(node.group)}
                >
                  {node.group}
                  <span className="admin-chev">▾</span>
                </button>
                <div className="admin-nav-items">
                  {node.items.map((it) => (
                    <NavLink
                      key={it.id}
                      to={`/admin/${it.id}`}
                      className={({ isActive }) =>
                        `admin-nav-item${isActive ? ' admin-nav-item--active' : ''}`
                      }
                    >
                      <span>{it.label}</span>
                      {it.id === 'members-pending' && pendingCount > 0 ? (
                        <span className="admin-badge">{pendingCount}</span>
                      ) : it.badge ? (
                        <span className="admin-badge">{it.badge}</span>
                      ) : null}
                    </NavLink>
                  ))}
                </div>
              </div>
            );
          })}
        </aside>

        <main className="admin-main">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
