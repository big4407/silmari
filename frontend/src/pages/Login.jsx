/** 로그인 UI — POST /api/v1/auth/login 연동 예정 (현재 폼만) */
import { Link } from "react-router-dom"
import LandingHeader from "../components/LandingHeader"
import "./AuthPage.css"

export default function Login() {
  return (
    <div className="auth-page">
      <LandingHeader />

      <main className="auth-page__main">
        <div className="auth-card">
          <h1 className="auth-card__title">로그인</h1>
          <p className="auth-card__desc">실마리 계정으로 로그인하세요.</p>

          <form className="auth-form" onSubmit={(e) => e.preventDefault()}>
            <label className="auth-form__label" htmlFor="login-email">
              이메일
            </label>
            <input
              id="login-email"
              className="auth-form__input"
              type="email"
              placeholder="example@email.com"
              autoComplete="email"
            />

            <label className="auth-form__label" htmlFor="login-password">
              비밀번호
            </label>
            <input
              id="login-password"
              className="auth-form__input"
              type="password"
              placeholder="비밀번호"
              autoComplete="current-password"
            />

            <button type="submit" className="auth-form__btn">
              로그인
            </button>
          </form>

          <p className="auth-card__footer">
            계정이 없으신가요? <Link to="/signup">회원가입</Link>
          </p>
        </div>
      </main>

      <footer className="auth-page__footer" />
    </div>
  )
}
