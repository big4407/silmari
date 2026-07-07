/**
 * 수사관 대시보드 공통 레이아웃 — 상단 탭 + Outlet.
 *
 * 하위: Dashboard, ChatbotPage, SearchResults
 */
import { Link, NavLink, Outlet } from 'react-router-dom';
import { isAuthenticated, isAdmin } from '../api/client';
import useLogout from '../hooks/useLogout';
import './DashboardLayout.css';

const TABS = [
  { to: '/dashboard', label: '실종자 검색', end: true },
  { to: '/dashboard/chatbot', label: '챗봇 검색' },
  { to: '/search-results', label: '검색 결과' },
];

export default function DashboardLayout() {
  const authed = isAuthenticated();
  const admin = isAdmin();
  const { doLogout } = useLogout();
  return (
    <div className="dashboard-layout">
      <header className="dashboard-layout__header">
        <div className="dashboard-layout__brand-bar">
          <div className="dashboard-layout__container dashboard-layout__brand-row">
            <div className="dashboard-layout__brand">
              <NavLink to="/" className="dashboard-layout__logo">
                실마리
              </NavLink>
              <span className="dashboard-layout__subtitle">
                실종자 통합 검색 시스템
              </span>
            </div>
            <div className="dashboard-layout__util">
              {admin && (
                <Link
                  to="/dev"
                  className="dashboard-layout__util-link dashboard-layout__util-link--temp"
                >
                  API 테스트
                </Link>
              )}
              {admin && (
                <Link
                  to="/admin"
                  className="dashboard-layout__util-link dashboard-layout__util-link--temp"
                >
                  관리자
                </Link>
              )}
              {authed ? (
                <button
                  type="button"
                  className="dashboard-layout__util-link"
                  onClick={doLogout}
                >
                  로그아웃
                </button>
              ) : (
                <Link to="/login" className="dashboard-layout__util-link">
                  로그인
                </Link>
              )}
            </div>
          </div>
        </div>
        <div className="dashboard-layout__nav-wrap">
          <nav className="dashboard-layout__nav" aria-label="주요 메뉴">
            {TABS.map((tab) => (
              <NavLink
                key={tab.to}
                to={tab.to}
                end={tab.end}
                className={({ isActive }) =>
                  `dashboard-layout__tab${isActive ? ' dashboard-layout__tab--active' : ''}`
                }
              >
                {tab.label}
              </NavLink>
            ))}
          </nav>
        </div>
      </header>

      <main className="dashboard-layout__content">
        <Outlet />
      </main>

      <footer className="dashboard-layout__footer">
        <span>실마리 실종자 통합 검색 시스템</span>
      </footer>
    </div>
  );
}
