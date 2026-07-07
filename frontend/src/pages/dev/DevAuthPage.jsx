import { useState } from "react"
import {
  login,
  bootstrapLogin,
  logout,
  refreshToken,
  fetchMe,
  fetchCaseSearchAccess,
} from "../../api/auth_api"
import { getStoredTokens, clearStoredTokens } from "../../api/devClient"
import ApiResult, { parseApiError } from "./components/ApiResult"
import "./DevCommon.css"

export default function DevAuthPage() {
  const [username, setUsername] = useState("")
  const [password, setPassword] = useState("")
  const [status, setStatus] = useState("idle")
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)

  const run = async (fn) => {
    setStatus("loading")
    setError(null)
    try {
      const result = await fn()
      setData(result ?? { message: "완료 (204 No Content)" })
      setStatus("ok")
    } catch (err) {
      setError(parseApiError(err))
      setStatus("err")
    }
  }

  const tokens = getStoredTokens()

  return (
    <>
      <h1 className="dev-page__title">인증</h1>
      <p className="dev-page__desc">
        JWT 토큰은 sessionStorage에 저장됩니다. 관리자 API는 admin 역할 토큰이 필요합니다.
      </p>

      <div className="dev-section">
        <h2>로그인</h2>
        <div className="dev-form">
          <label htmlFor="dev-login-user">아이디</label>
          <input
            id="dev-login-user"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder="username"
          />
          <label htmlFor="dev-login-pw">비밀번호</label>
          <input
            id="dev-login-pw"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
          <div className="dev-form__row">
            <button
              type="button"
              className="dev-btn"
              disabled={!username || !password}
              onClick={() => run(() => login(username, password))}
            >
              POST /api/v1/auth/login
            </button>
            <button
              type="button"
              className="dev-btn dev-btn--secondary"
              onClick={() => run(bootstrapLogin)}
            >
              POST bootstrap-login (로컬)
            </button>
          </div>
        </div>
      </div>

      <div className="dev-section">
        <h2>토큰 · 세션</h2>
        <div className="dev-form__row">
          <button
            type="button"
            className="dev-btn dev-btn--secondary"
            disabled={!tokens?.refresh_token}
            onClick={() => run(() => refreshToken(tokens.refresh_token))}
          >
            POST /auth/refresh
          </button>
          <button
            type="button"
            className="dev-btn dev-btn--secondary"
            disabled={!tokens}
            onClick={() => run(logout)}
          >
            POST /auth/logout
          </button>
          <button
            type="button"
            className="dev-btn dev-btn--danger"
            onClick={() => {
              clearStoredTokens()
              setData({ message: "토큰 삭제됨" })
              setStatus("ok")
              setError(null)
            }}
          >
            토큰 초기화
          </button>
        </div>
        {tokens && (
          <p style={{ fontSize: "0.8rem", color: "var(--color-text-secondary)" }}>
            access_token: {tokens.access_token?.slice(0, 24)}…
          </p>
        )}
      </div>

      <div className="dev-section">
        <h2>보호 API</h2>
        <div className="dev-form__row">
          <button
            type="button"
            className="dev-btn"
            disabled={!tokens}
            onClick={() => run(fetchMe)}
          >
            GET /api/v1/users/me
          </button>
          <button
            type="button"
            className="dev-btn dev-btn--secondary"
            disabled={!tokens}
            onClick={() => run(fetchCaseSearchAccess)}
          >
            GET /operations/case-search (수사관)
          </button>
        </div>
        <ApiResult status={status} data={data} error={error} />
      </div>
    </>
  )
}
