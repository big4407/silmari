/** 로그인 UI — POST /api/v1/auth/login 연동 */
import { useState } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import LandingHeader from '../components/LandingHeader';
import { login } from '../api/client';
import './AuthPage.css';

const FEATURES = [
  { icon: '01', text: 'AI 이미지 분석으로 인상착의 기반 실종자 검색' },
  { icon: '02', text: '안전안내문자 연동 실시간 매칭 알림' },
  { icon: '03', text: 'CCTV 영상 분석 및 검색 이력 관리' },
];

export default function Login() {
  const navigate = useNavigate();
  const location = useLocation();
  const from = location.state?.from?.pathname || '/dashboard';
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await login(username, password);
      navigate(from, { replace: true });
    } catch (err) {
      const status = err?.response?.status;
      if (status === 401) {
        setError('아이디 또는 비밀번호가 올바르지 않습니다.');
      } else if (status === 403) {
        setError('아직 승인되지 않았거나 비활성화된 계정입니다.');
      } else {
        setError('로그인에 실패했습니다. 잠시 후 다시 시도해 주세요.');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-page">
      <LandingHeader />

      <main className="auth-page__main">
        <div className="auth-shell">
          <aside className="auth-panel">
            <p className="auth-panel__eyebrow">Silmari Account</p>
            <h2 className="auth-panel__title">실종자 검색을 시작하세요</h2>
            <p className="auth-panel__desc">
              실마리는 AI 이미지 분석과 안전안내문자 연동으로 실종자를 빠르게
              찾는 통합 검색 시스템입니다.
            </p>
            <ul className="auth-panel__features">
              {FEATURES.map((item) => (
                <li key={item.icon}>
                  <span className="auth-panel__feature-icon">{item.icon}</span>
                  {item.text}
                </li>
              ))}
            </ul>
          </aside>

          <div className="auth-card">
            <h1 className="auth-card__title">로그인</h1>
            <p className="auth-card__desc">실마리 계정으로 로그인하세요.</p>

            <form className="auth-form" onSubmit={handleSubmit}>
              <div className="auth-form__field">
                <label className="auth-form__label" htmlFor="login-username">
                  아이디
                </label>
                <input
                  id="login-username"
                  className="auth-form__input"
                  type="text"
                  placeholder="아이디"
                  autoComplete="username"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  required
                />
              </div>

              <div className="auth-form__field">
                <label className="auth-form__label" htmlFor="login-password">
                  비밀번호
                </label>
                <input
                  id="login-password"
                  className="auth-form__input"
                  type="password"
                  placeholder="비밀번호"
                  autoComplete="current-password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                />
              </div>

              {error && <p className="auth-form__error">{error}</p>}

              <button type="submit" className="auth-form__btn" disabled={loading}>
                {loading ? '로그인 중…' : '로그인'}
              </button>
            </form>

            <p className="auth-card__footer">
              계정이 없으신가요? <Link to="/signup">회원가입</Link>
            </p>
          </div>
        </div>
      </main>
    </div>
  );
}
