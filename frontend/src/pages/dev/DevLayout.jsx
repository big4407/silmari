import { Link, Outlet, useLocation } from "react-router-dom"
import { API_BASE, getStoredTokens } from "../../api/devClient"
import { DEV_PAGES } from "./devConfig"
import "./DevLayout.css"

export default function DevLayout() {
  const { pathname } = useLocation()
  const tokens = getStoredTokens()
  const subPath = pathname.replace(/^\/dev\/?/, "")

  return (
    <div className="dev-layout">
      <aside className="dev-sidebar">
        <div className="dev-sidebar__head">
          <Link to="/dev" className="dev-sidebar__title">API 테스트</Link>
          <span className="dev-sidebar__badge">DEV</span>
        </div>
        <p className="dev-sidebar__base">{API_BASE}</p>
        <p className={`dev-sidebar__auth ${tokens ? "dev-sidebar__auth--ok" : ""}`}>
          {tokens ? "토큰 있음" : "토큰 없음"}
        </p>
        <nav className="dev-sidebar__nav">
          {DEV_PAGES.map((page) => {
            const to = page.path ? `/dev/${page.path}` : "/dev"
            const active = subPath === page.path
            return (
              <Link
                key={page.path || "index"}
                to={to}
                className={`dev-sidebar__link${active ? " dev-sidebar__link--active" : ""}`}
              >
                {page.label}
              </Link>
            )
          })}
        </nav>
        <Link to="/" className="dev-sidebar__back">← 서비스로 돌아가기</Link>
        <Link to="/admin" className="dev-sidebar__back">관리자 콘솔</Link>
      </aside>
      <main className="dev-main">
        <Outlet />
      </main>
    </div>
  )
}
