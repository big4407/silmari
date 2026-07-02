import { Link } from "react-router-dom"
import { DEV_PAGES } from "./devConfig"
import "./DevCommon.css"

/** /dev 홈 — devConfig 메뉴 목록을 카드 그리드로 표시 */
export default function DevHub() {
  return (
    <>
      <h1 className="dev-page__title">API 테스트 허브</h1>
      <p className="dev-page__desc">
        백엔드 API 연동을 기능별로 빠르게 검증합니다. 인증이 필요한 API는 먼저{" "}
        <Link to="/dev/auth">인증</Link> 페이지에서 로그인하세요.
      </p>
      <div className="dev-hub__grid">
        {DEV_PAGES.filter((p) => p.path).map((page) => (
          <Link key={page.path} to={`/dev/${page.path}`} className="dev-hub__card">
            <h3>{page.label}</h3>
            <p>{page.desc}</p>
          </Link>
        ))}
      </div>
    </>
  )
}
