import { useState } from 'react';
import { Link, NavLink, Outlet, useLocation } from 'react-router-dom';
import AdminConsoleSwitch from '../../components/AdminConsoleSwitch';
import { DEV_NAV } from './devConfig';
import useLogout from '../../hooks/useLogout';
import '../admin/AdminLayout.css';
import './DevLayout.css';

/** /dev/* 공통 레이아웃 — 관리자 콘솔과 동일한 상단바·사이드바 */
export default function DevLayout() {
  const { pathname } = useLocation();
  const { doLogout } = useLogout();
  const subPath = pathname.replace(/^\/dev\/?/, '');

  const [collapsed, setCollapsed] = useState(() =>
    Object.fromEntries(
      DEV_NAV.filter((node) => node.group).map((node, i) => [node.group, i > 1]),
    ),
  );

  const toggleGroup = (key) => {
    setCollapsed((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  return (
    <div className="admin-console dev-console">
      <header className="admin-topbar">
        <div className="admin-brand">
          <Link to="/" className="admin-logo">
            실마리
          </Link>
          <span className="admin-sub">API 테스트</span>
        </div>
        <div className="admin-right">
          <AdminConsoleSwitch mode="dev" />
          <span className="admin-divider" />
          <a href="#help">도움</a>
          <span className="admin-divider" />
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
          {DEV_NAV.map((node) => {
            if (node.solo) {
              return (
                <NavLink
                  key={node.path || 'overview'}
                  to="/dev"
                  end
                  className={({ isActive }) =>
                    `admin-nav-solo${isActive ? ' admin-nav-solo--active' : ''}`
                  }
                >
                  <span>▣</span> {node.label}
                </NavLink>
              );
            }

            const isCollapsed = collapsed[node.group] ?? false;

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
                  {node.items.map((item) => (
                    <NavLink
                      key={item.path}
                      to={`/dev/${item.path}`}
                      className={({ isActive }) =>
                        `admin-nav-item${isActive ? ' admin-nav-item--active' : ''}`
                      }
                    >
                      <span>{item.label}</span>
                    </NavLink>
                  ))}
                </div>
              </div>
            );
          })}
        </aside>

        <main className="admin-main">
          <Outlet key={subPath} />
        </main>
      </div>
    </div>
  );
}
