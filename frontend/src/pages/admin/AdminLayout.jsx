/**
 * 관리자 콘솔 레이아웃 — navConfig 기반 사이드바 + 뷰 라우팅.
 *
 * 하위: AdminViewPage (:viewId) — 회원·메시지·검색운영·감사 등
 */
import { useState } from 'react';
import { Link, NavLink, Outlet } from 'react-router-dom';
import { NAV } from './navConfig';
import useLogout from '../../hooks/useLogout';
import './AdminLayout.css';

export default function AdminLayout() {
  const [collapsed, setCollapsed] = useState(() =>
    Object.fromEntries(NAV.map((node, i) => [node.group || node.id, i > 3])),
  );
  const { doLogout } = useLogout();

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
          <Link to="/dev" className="admin-dev-link">
            API 테스트
          </Link>
          <span className="admin-divider" />
          <span className="admin-role">시스템 관리자</span>
          <span className="admin-divider" />
          <a href="#help">도움</a>
          <a
            href="#logout"
            onClick={(e) => {
              e.preventDefault();
              doLogout();
            }}
          >
            로그아웃
          </a>
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
                      {it.badge ? (
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
