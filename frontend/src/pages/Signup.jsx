/** 회원가입 UI — POST /api/v1/auth/signup (승인 대기 상태로 신청) */
import { Link } from 'react-router-dom';
import LandingHeader from '../components/LandingHeader';
import './AuthPage.css';

export default function Signup() {
  return (
    <div className="auth-page">
      <LandingHeader />

      <main className="auth-page__main">
        <div className="auth-card">
          <h1 className="auth-card__title">회원가입</h1>
          <p className="auth-card__desc">
            실마리 서비스 이용을 위해 계정을 만드세요.
          </p>

          <form className="auth-form" onSubmit={(e) => e.preventDefault()}>
            <label className="auth-form__label" htmlFor="signup-name">
              이름
            </label>
            <input
              id="signup-name"
              className="auth-form__input"
              type="text"
              placeholder="이름"
              autoComplete="name"
            />

            <label className="auth-form__label" htmlFor="signup-email">
              이메일
            </label>
            <input
              id="signup-email"
              className="auth-form__input"
              type="email"
              placeholder="example@email.com"
              autoComplete="email"
            />

            <label className="auth-form__label" htmlFor="signup-password">
              비밀번호
            </label>
            <input
              id="signup-password"
              className="auth-form__input"
              type="password"
              placeholder="8자 이상"
              autoComplete="new-password"
            />

            <label
              className="auth-form__label"
              htmlFor="signup-password-confirm"
            >
              비밀번호 확인
            </label>
            <input
              id="signup-password-confirm"
              className="auth-form__input"
              type="password"
              placeholder="비밀번호 확인"
              autoComplete="new-password"
            />

            <button type="submit" className="auth-form__btn">
              회원가입
            </button>
          </form>

          <p className="auth-card__footer">
            이미 계정이 있으신가요? <Link to="/login">로그인</Link>
          </p>
        </div>
      </main>

      <footer className="auth-page__footer" />
    </div>
  );
}
