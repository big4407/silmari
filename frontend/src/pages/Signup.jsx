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

const STEPS = [
  { icon: '1', text: '회원가입 신청서 작성' },
  { icon: '2', text: '관리자 승인 대기' },
  { icon: '3', text: '승인 후 서비스 이용' },
];

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
        <div className="auth-shell auth-shell--wide">
          <aside className="auth-panel">
            <p className="auth-panel__eyebrow">Join Silmari</p>
            <h2 className="auth-panel__title">회원가입 신청</h2>
            <p className="auth-panel__desc">
              수사관·행정담당자 등 공공기관 소속 사용자만 가입할 수 있습니다.
              승인 후 실종자 통합 검색 서비스를 이용하실 수 있습니다.
            </p>
            <ul className="auth-panel__features">
              {STEPS.map((item) => (
                <li key={item.icon}>
                  <span className="auth-panel__feature-icon">{item.icon}</span>
                  {item.text}
                </li>
              ))}
            </ul>
            <p className="auth-panel__notice">
              가입 신청 후 관리자 검토가 필요합니다. 승인까지 1~2영업일이
              소요될 수 있습니다.
            </p>
          </aside>

          <div className="auth-card">
            <h1 className="auth-card__title">회원가입</h1>
            <p className="auth-card__desc">
              아래 정보를 입력해 주세요. 관리자 승인 후 이용 가능합니다.
            </p>

            <form className="auth-form" onSubmit={handleSubmit}>
              <div className="auth-form__section">
                <h3 className="auth-form__section-title">기본 정보</h3>
                <div className="auth-form__grid">
                  <div className="auth-form__field">
                    <label
                      className="auth-form__label"
                      htmlFor="signup-username"
                    >
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
                  </div>
                  <div className="auth-form__field">
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
                  </div>
                  <div className="auth-form__field auth-form__field--full">
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
                  </div>
                </div>
              </div>

              <div className="auth-form__section">
                <h3 className="auth-form__section-title">소속</h3>
                <div className="auth-form__grid">
                  <div className="auth-form__field auth-form__field--full">
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
                  </div>
                  <div className="auth-form__field">
                    <label
                      className="auth-form__label"
                      htmlFor="signup-department"
                    >
                      부서
                    </label>
                    <input
                      id="signup-department"
                      className="auth-form__input"
                      type="text"
                      placeholder="선택 입력"
                      value={form.department}
                      onChange={update('department')}
                    />
                  </div>
                  <div className="auth-form__field">
                    <label
                      className="auth-form__label"
                      htmlFor="signup-position"
                    >
                      직위
                    </label>
                    <input
                      id="signup-position"
                      className="auth-form__input"
                      type="text"
                      placeholder="선택 입력"
                      value={form.position}
                      onChange={update('position')}
                    />
                  </div>
                  <div className="auth-form__field auth-form__field--full">
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
                  </div>
                </div>
              </div>

              <div className="auth-form__section">
                <h3 className="auth-form__section-title">비밀번호</h3>
                <div className="auth-form__grid">
                  <div className="auth-form__field">
                    <label
                      className="auth-form__label"
                      htmlFor="signup-password"
                    >
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
                  </div>
                  <div className="auth-form__field">
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
                  </div>
                </div>
              </div>

              {error && <p className="auth-form__error">{error}</p>}

              <button type="submit" className="auth-form__btn" disabled={loading}>
                {loading ? '신청 중…' : '회원가입 신청'}
              </button>
            </form>

            <p className="auth-card__footer">
              이미 계정이 있으신가요? <Link to="/login">로그인</Link>
            </p>
          </div>
        </div>
      </main>

      <footer className="auth-page__footer" />
    </div>
  );
}
