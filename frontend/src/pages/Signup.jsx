/** 회원가입 UI — POST /member/auth/signup (승인 대기 상태로 신청) */
import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import LandingHeader from '../components/LandingHeader';
import { signup } from '../api/client';
import './AuthPage.css';

const INITIAL = {
  username: '',
  email: '',
  password: '',
  passwordConfirm: '',
  full_name: '',
  organization: '',
  phone: '',
  department: '',
  position: '',
};

export default function Signup() {
  const navigate = useNavigate();
  const [form, setForm] = useState(INITIAL);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const update = (key) => (e) =>
    setForm((prev) => ({ ...prev, [key]: e.target.value }));

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    if (form.password !== form.passwordConfirm) {
      setError('비밀번호가 일치하지 않습니다.');
      return;
    }
    if (form.password.length < 12) {
      setError('비밀번호는 12자 이상이어야 합니다.');
      return;
    }

    setLoading(true);
    try {
      await signup({
        username: form.username,
        email: form.email,
        password: form.password,
        full_name: form.full_name,
        organization: form.organization,
        phone: form.phone,
        department: form.department || null,
        position: form.position || null,
      });
      alert(
        '회원가입 신청이 접수되었습니다. 관리자 승인 후 로그인할 수 있습니다.',
      );
      navigate('/login');
    } catch (err) {
      const status = err?.response?.status;
      const detail = err?.response?.data?.detail;
      if (status === 409) {
        setError('이미 사용 중인 아이디 또는 이메일입니다.');
      } else if (status === 422) {
        setError('입력값을 확인해 주세요. (아이디 3자↑, 비밀번호 12자↑ 등)');
      } else if (typeof detail === 'string') {
        setError(detail);
      } else {
        setError('회원가입에 실패했습니다. 잠시 후 다시 시도해 주세요.');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-page">
      <LandingHeader />

      <main className="auth-page__main">
        <div className="auth-card">
          <h1 className="auth-card__title">회원가입</h1>
          <p className="auth-card__desc">
            실마리 서비스 이용을 위해 계정을 만드세요. (관리자 승인 후 이용
            가능)
          </p>

          <form className="auth-form" onSubmit={handleSubmit}>
            <label className="auth-form__label" htmlFor="signup-username">
              아이디
            </label>
            <input
              id="signup-username"
              className="auth-form__input"
              type="text"
              placeholder="영문/숫자 3자 이상"
              autoComplete="username"
              value={form.username}
              onChange={update('username')}
              required
            />

            <label className="auth-form__label" htmlFor="signup-name">
              이름
            </label>
            <input
              id="signup-name"
              className="auth-form__input"
              type="text"
              placeholder="이름"
              autoComplete="name"
              value={form.full_name}
              onChange={update('full_name')}
              required
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
              value={form.email}
              onChange={update('email')}
              required
            />

            <label className="auth-form__label" htmlFor="signup-org">
              소속 기관
            </label>
            <input
              id="signup-org"
              className="auth-form__input"
              type="text"
              placeholder="소속 기관"
              value={form.organization}
              onChange={update('organization')}
              required
            />

            <label className="auth-form__label" htmlFor="signup-phone">
              연락처
            </label>
            <input
              id="signup-phone"
              className="auth-form__input"
              type="tel"
              placeholder="010-0000-0000"
              autoComplete="tel"
              value={form.phone}
              onChange={update('phone')}
              required
            />

            <label className="auth-form__label" htmlFor="signup-password">
              비밀번호
            </label>
            <input
              id="signup-password"
              className="auth-form__input"
              type="password"
              placeholder="12자 이상"
              autoComplete="new-password"
              value={form.password}
              onChange={update('password')}
              required
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
              value={form.passwordConfirm}
              onChange={update('passwordConfirm')}
              required
            />

            {error && <p className="auth-form__error">{error}</p>}

            <button type="submit" className="auth-form__btn" disabled={loading}>
              {loading ? '신청 중…' : '회원가입'}
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
