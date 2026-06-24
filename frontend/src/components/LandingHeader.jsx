import { Link, useLocation } from "react-router-dom"
import "./LandingHeader.css"

const NAV_LINKS = [
  { to: "/dashboard", label: "실종자 검색" },
  { to: "/dashboard/chatbot", label: "챗봇 검색" },
  { to: "/search-results", label: "검색 결과" },
  { to: "/dashboard/history", label: "검색 이력" },
]

export default function LandingHeader() {
  const { pathname } = useLocation()

  return (
    <header className="landing-header">
      <Link to="/" className="landing-header__logo">
        실마리 로고
      </Link>
      <div className="landing-header__actions">
        <Link
          to="/login"
          className={`landing-header__btn${pathname === "/login" ? " landing-header__btn--active" : ""}`}
        >
          로그인
        </Link>
        <Link
          to="/signup"
          className={`landing-header__btn${pathname === "/signup" ? " landing-header__btn--active" : ""}`}
        >
          회원가입
        </Link>
        {NAV_LINKS.map((item) => (
          <Link
            key={item.to}
            to={item.to}
            className="landing-header__btn landing-header__btn--nav"
          >
            {item.label}
          </Link>
        ))}
      </div>
    </header>
  )
}
