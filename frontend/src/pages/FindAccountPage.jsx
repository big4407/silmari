/** 아이디/비밀번호 찾기 — 이름+이메일(+아이디) 본인확인 후 즉시 처리(이메일 인증 없음) */
import { useState } from 'react';
import { Link } from 'react-router-dom';
import LandingHeader from '../components/LandingHeader';
import { findUsername, resetPassword } from '../api/client';
import './AuthPage.css';

function FindUsernameForm() {
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setResult('');
    setLoading(true);
    try {
      const data = await findUsername({ full_name: fullName, email });
      setResult(data.username);
    } catch (err) {
      const status = err?.response?.status;
      setError(
        status === 404
          ? '입력하신 정보와 일치하는 계정을 찾을 수 없습니다.'
          : '아이디 찾기에 실패했습니다. 잠시 후 다시 시도해 주세요.',
      );
    } finally {
      setLoading(false);
    }
  };

  if (result) {
    return (
      <div className="auth-form__result">
        <p className="auth-form__result-label">회원님의 아이디는</p>
        <p className="auth-form__result-value">{result}</p>
        <p className="auth-form__result-label">입니다.</p>
        <Link to="/login" className="auth-form__btn auth-form__btn--link">
          로그인하러 가기
        </Link>
      </div>
    );
  }

  return (
    <form className="auth-form" onSubmit={handleSubmit}>
      <div className="auth-form__field">
        <label className="auth-form__label" htmlFor="find-id-name">
          이름
        </label>
        <input
          id="find-id-name"
          className="auth-form__input"
          type="text"
          value={fullName}
          onChange={(e) => setFullName(e.target.value)}
          required
        />
      </div>
      <div className="auth-form__field">
        <label className="auth-form__label" htmlFor="find-id-email">
          이메일
        </label>
        <input
          id="find-id-email"
          className="auth-form__input"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
        />
      </div>

      {error && <p className="auth-form__error">{error}</p>}

      <button type="submit" className="auth-form__btn" disabled={loading}>
        {loading ? '확인 중…' : '아이디 찾기'}
      </button>
    </form>
  );
}

function ResetPasswordForm() {
  const [username, setUsername] = useState('');
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [newPasswordConfirm, setNewPasswordConfirm] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [done, setDone] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    if (newPassword !== newPasswordConfirm) {
      setError('새 비밀번호가 일치하지 않습니다.');
      return;
    }
    if (newPassword.length < 12) {
      setError('비밀번호는 12자 이상이어야 합니다.');
      return;
    }

    setLoading(true);
    try {
      await resetPassword({
        username,
        full_name: fullName,
        email,
        new_password: newPassword,
      });
      setDone(true);
    } catch (err) {
      const status = err?.response?.status;
      setError(
        status === 404
          ? '입력하신 정보와 일치하는 계정을 찾을 수 없습니다.'
          : '비밀번호 재설정에 실패했습니다. 잠시 후 다시 시도해 주세요.',
      );
    } finally {
      setLoading(false);
    }
  };

  if (done) {
    return (
      <div className="auth-form__result">
        <p className="auth-form__result-label">비밀번호가 변경되었습니다.</p>
        <Link to="/login" className="auth-form__btn auth-form__btn--link">
          로그인하러 가기
        </Link>
      </div>
    );
  }

  return (
    <form className="auth-form" onSubmit={handleSubmit}>
      <div className="auth-form__section">
        <h3 className="auth-form__section-title">본인확인</h3>
        <div className="auth-form__grid">
          <div className="auth-form__field">
            <label className="auth-form__label" htmlFor="reset-username">
              아이디
            </label>
            <input
              id="reset-username"
              className="auth-form__input"
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
            />
          </div>
          <div className="auth-form__field">
            <label className="auth-form__label" htmlFor="reset-name">
              이름
            </label>
            <input
              id="reset-name"
              className="auth-form__input"
              type="text"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              required
            />
          </div>
          <div className="auth-form__field auth-form__field--full">
            <label className="auth-form__label" htmlFor="reset-email">
              이메일
            </label>
            <input
              id="reset-email"
              className="auth-form__input"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>
        </div>
      </div>

      <div className="auth-form__section">
        <h3 className="auth-form__section-title">새 비밀번호</h3>
        <div className="auth-form__grid">
          <div className="auth-form__field">
            <label className="auth-form__label" htmlFor="reset-new-password">
              새 비밀번호
            </label>
            <input
              id="reset-new-password"
              className="auth-form__input"
              type="password"
              placeholder="12자 이상"
              autoComplete="new-password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              required
            />
          </div>
          <div className="auth-form__field">
            <label className="auth-form__label" htmlFor="reset-new-password-confirm">
              새 비밀번호 확인
            </label>
            <input
              id="reset-new-password-confirm"
              className="auth-form__input"
              type="password"
              autoComplete="new-password"
              value={newPasswordConfirm}
              onChange={(e) => setNewPasswordConfirm(e.target.value)}
              required
            />
          </div>
        </div>
      </div>

      {error && <p className="auth-form__error">{error}</p>}

      <button type="submit" className="auth-form__btn" disabled={loading}>
        {loading ? '변경 중…' : '비밀번호 변경'}
      </button>
    </form>
  );
}

export default function FindAccountPage() {
  const [tab, setTab] = useState('username'); // 'username' | 'password'

  return (
    <div className="auth-page">
      <LandingHeader />

      <main className="auth-page__main">
        <div className="auth-shell">
          <aside className="auth-panel">
            <p className="auth-panel__eyebrow">Find Account</p>
            <h2 className="auth-panel__title">아이디·비밀번호 찾기</h2>
            <p className="auth-panel__desc">
              가입 시 등록한 이름과 이메일로 본인확인 후 바로 처리됩니다. 이메일로
              인증 링크가 발송되지는 않습니다.
            </p>
            <p className="auth-panel__notice">
              본인확인 정보가 정확히 일치해야 처리됩니다. 정보가 기억나지 않으면
              관리자에게 문의해 주세요.
            </p>
          </aside>

          <div className="auth-card">
            <div className="auth-card__tabs">
              <button
                type="button"
                className={`auth-card__tab ${tab === 'username' ? 'auth-card__tab--active' : ''}`}
                onClick={() => setTab('username')}
              >
                아이디 찾기
              </button>
              <button
                type="button"
                className={`auth-card__tab ${tab === 'password' ? 'auth-card__tab--active' : ''}`}
                onClick={() => setTab('password')}
              >
                비밀번호 찾기
              </button>
            </div>

            {tab === 'username' ? <FindUsernameForm /> : <ResetPasswordForm />}

            <p className="auth-card__footer">
              <Link to="/login">로그인으로 돌아가기</Link>
            </p>
          </div>
        </div>
      </main>

      <footer className="auth-page__footer" />
    </div>
  );
}
