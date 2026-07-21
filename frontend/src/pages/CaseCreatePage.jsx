/**
 * 새 실종자 케이스 등록 — 개별 입력, 또는 챗봇에서 넘어올 때 쿼리스트링으로 값 미리 채움
 * (예: /dashboard/cases/new?missing_name=...&gender=M&age=30&clothing=...&missing_location=...).
 * 등록자가 자동으로 담당수사관이 되고, 상태는 바로 진행중으로 시작한다(백엔드 처리).
 *
 * 로그인/회원가입 폼(auth-*) 대신, 평범한 "게시글 작성" 페이지 톤으로 —
 * CasesPage.jsx와 같은 색상·타이포 언어를 써서 프로젝트에 자연스럽게 어울리게.
 */
import { useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { createMissingPersonCase, getRole } from '../api/client';
import './CaseCreatePage.css';

export default function CaseCreatePage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const canWrite = getRole() !== '3';

  const [missingName, setMissingName] = useState(
    searchParams.get('missing_name') ?? '',
  );
  const [gender, setGender] = useState(searchParams.get('gender') ?? '');
  const [age, setAge] = useState(searchParams.get('age') ?? '');
  const [clothing, setClothing] = useState(searchParams.get('clothing') ?? '');
  const [missingLocation, setMissingLocation] = useState(
    searchParams.get('missing_location') ?? '',
  );
  const [notes, setNotes] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  async function handleSubmit(e) {
    e.preventDefault();
    if (!canWrite) return;
    setError('');
    setSubmitting(true);
    try {
      const created = await createMissingPersonCase({
        missing_name: missingName || null,
        gender: gender || null,
        age: age ? Number(age) : null,
        clothing: clothing || null,
        missing_location: missingLocation || null,
        notes: notes || null,
      });
      navigate(`/dashboard/cases?highlight=${created.id}`);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : '케이스 등록에 실패했습니다.',
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="case-form">
      <header className="case-form__header">
        <h1>새 케이스 등록</h1>
        <p className="case-form__desc">
          안내문자에 안 묶인 실종자 정보를 직접 등록합니다. 등록하면 바로 본인이
          담당자로 배정됩니다.
        </p>
      </header>

      <div className="case-form__panel">
        {!canWrite && (
          <p className="case-form__notice">
            공무원 계정은 조회만 가능합니다 — 케이스 등록은 수사관·관리자
            계정으로 로그인해 주세요.
          </p>
        )}

        <form onSubmit={handleSubmit}>
          <section className="case-form__section">
            <h2 className="case-form__section-title">기본 정보</h2>

            <div className="case-form__row">
              <div className="case-form__field">
                <label htmlFor="case-name">이름</label>
                <input
                  id="case-name"
                  type="text"
                  value={missingName}
                  onChange={(e) => setMissingName(e.target.value)}
                  disabled={!canWrite}
                  placeholder="이름을 모르면 비워두어도 됩니다"
                />
              </div>
              <div className="case-form__field case-form__field--sm">
                <label htmlFor="case-gender">성별</label>
                <select
                  id="case-gender"
                  value={gender}
                  onChange={(e) => setGender(e.target.value)}
                  disabled={!canWrite}
                >
                  <option value="">선택 안 함</option>
                  <option value="M">남</option>
                  <option value="F">여</option>
                </select>
              </div>
              <div className="case-form__field case-form__field--sm">
                <label htmlFor="case-age">나이</label>
                <input
                  id="case-age"
                  type="number"
                  min={0}
                  max={150}
                  value={age}
                  onChange={(e) => setAge(e.target.value)}
                  disabled={!canWrite}
                />
              </div>
            </div>

            <div className="case-form__row">
              <div className="case-form__field">
                <label htmlFor="case-location">지역</label>
                <input
                  id="case-location"
                  type="text"
                  placeholder="예: 서울 관악구"
                  value={missingLocation}
                  onChange={(e) => setMissingLocation(e.target.value)}
                  disabled={!canWrite}
                />
              </div>
              <div className="case-form__field">
                <label htmlFor="case-clothing">인상착의</label>
                <input
                  id="case-clothing"
                  type="text"
                  value={clothing}
                  onChange={(e) => setClothing(e.target.value)}
                  disabled={!canWrite}
                />
              </div>
            </div>
          </section>

          <section className="case-form__section">
            <h2 className="case-form__section-title">메모</h2>
            <div className="case-form__field case-form__field--full">
              <label htmlFor="case-notes">비고</label>
              <textarea
                id="case-notes"
                rows={5}
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                disabled={!canWrite}
                placeholder="파악한 정황이나 참고 사항을 자유롭게 남겨주세요"
              />
            </div>
          </section>

          {error && <p className="case-form__error">{error}</p>}

          <div className="case-form__actions">
            <button
              type="button"
              className="case-form__btn case-form__btn--ghost"
              onClick={() => navigate('/dashboard/cases')}
            >
              취소
            </button>
            <button
              type="submit"
              className="case-form__btn case-form__btn--primary"
              disabled={submitting || !canWrite}
            >
              {submitting ? '등록 중…' : '케이스 등록'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
