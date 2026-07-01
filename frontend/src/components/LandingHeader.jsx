/** 랜딩·인증 페이지 공통 헤더 네비게이션 */
import { Link, NavLink, useLocation } from 'react-router-dom';
import './LandingHeader.css';

const TABS = [
  { to: '/dashboard', label: '실종자 검색', end: true },
  { to: '/dashboard/chatbot', label: '챗봇 검색' },
  { to: '/search-results', label: '검색 결과' },
  { to: '/dashboard/history', label: '검색 이력' },
];

export default function LandingHeader() {
  const { pathname } = useLocation();

  return (
    <header className="landing-header">
      <div className="landing-header__brand-bar">
        <div className="landing-header__container landing-header__brand-row">
          <div className="landing-header__brand">
            <Link to="/" className="landing-header__logo">
              실마리
            </Link>
            <span className="landing-header__subtitle">
              실종자 통합 검색 시스템
            </span>
          </div>
          <div className="landing-header__util">
            <Link
              to="/dev"
              className="landing-header__util-link landing-header__util-link--temp"
            >
              API 테스트
            </Link>
            <Link
              to="/admin"
              className="landing-header__util-link landing-header__util-link--temp"
            >
              관리자
            </Link>
            <Link
              to="/login"
              className={`landing-header__util-link${pathname === '/login' ? ' landing-header__util-link--active' : ''}`}
            >
              로그인
            </Link>
            <Link
              to="/signup"
              className={`landing-header__util-link${pathname === '/signup' ? ' landing-header__util-link--active' : ''}`}
            >
              회원가입
            </Link>
          </div>
        </div>
      </div>
      <div className="landing-header__nav-wrap">
        <nav className="landing-header__nav" aria-label="주요 메뉴">
          {TABS.map((tab) => (
            <NavLink
              key={tab.to}
              to={tab.to}
              end={tab.end}
              className={({ isActive }) =>
                `landing-header__tab${isActive ? ' landing-header__tab--active' : ''}`
              }
            >
              {tab.label}
            </NavLink>
          ))}
        </nav>
      </div>
    </header>
  );
}
