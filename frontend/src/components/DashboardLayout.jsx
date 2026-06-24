import { Link, NavLink, Outlet } from "react-router-dom"
import "./DashboardLayout.css"

const TABS = [
  { to: "/dashboard", label: "실종자 검색", end: true },
  { to: "/dashboard/chatbot", label: "챗봇 검색" },
  { to: "/search-results", label: "검색 결과" },
  { to: "/dashboard/history", label: "검색 이력" },
]

export default function DashboardLayout() {
  return (
    <div className="dashboard-layout">
      <header className="dashboard-layout__header">
        <div className="dashboard-layout__brand-bar">
          <div className="dashboard-layout__container dashboard-layout__brand-row">
            <div className="dashboard-layout__brand">
              <NavLink to="/" className="dashboard-layout__logo">
                실마리
              </NavLink>
              <span className="dashboard-layout__subtitle">실종자 통합 검색 시스템</span>
            </div>
            <div className="dashboard-layout__util">
              <Link to="/login" className="dashboard-layout__util-link">
                로그인
              </Link>
            </div>
          </div>
        </div>
        <div className="dashboard-layout__nav-wrap">
          <nav className="dashboard-layout__container dashboard-layout__nav" aria-label="주요 메뉴">
            {TABS.map((tab) => (
              <NavLink
                key={tab.to}
                to={tab.to}
                end={tab.end}
                className={({ isActive }) =>
                  `dashboard-layout__tab${isActive ? " dashboard-layout__tab--active" : ""}`
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
  )
}
