/** 영상 내 인상착의 매칭 후보 목록 — 세로 스크롤, 클릭 시 해당 클립 재생 */
import './DetectionCandidateList.css';

function formatTime(sec) {
  if (sec == null || Number.isNaN(sec)) return '-';
  const min = Math.floor(sec / 60);
  const s = (sec % 60).toFixed(1);
  return min > 0 ? `${min}분 ${s}초` : `${s}초`;
}

export default function DetectionCandidateList({
  candidates,
  activeIndex = 0,
  onSelect,
  appearance,
}) {
  if (!candidates?.length) {
    return (
      <aside className="candidate-list candidate-list--empty">
        <h3>탐지 후보</h3>
        <p className="candidate-list__empty-msg">
          이 영상에서 인상착의에 해당하는 후보가 없습니다.
        </p>
      </aside>
    );
  }

  return (
    <aside className="candidate-list">
      <header className="candidate-list__header">
        <h3>탐지 후보</h3>
        <span className="candidate-list__count">{candidates.length}명</span>
      </header>
      {appearance && (
        <p className="candidate-list__filter">
          인상착의: <strong>{appearance}</strong>
        </p>
      )}
      <ul className="candidate-list__items">
        {candidates.map((candidate, index) => {
          const isActive = index === activeIndex;

          return (
            <li key={candidate.filename || index}>
              <button
                type="button"
                className={`candidate-list__item${
                  isActive ? ' candidate-list__item--active' : ''
                }`}
                onClick={() => onSelect?.(index)}
                aria-pressed={isActive}
              >
                <div className="candidate-list__thumb-wrap">
                  {candidate.thumbnail_url ? (
                    <img
                      src={candidate.thumbnail_url}
                      alt={`후보 ${candidate.candidate_index ?? index + 1}`}
                      className="candidate-list__thumb"
                    />
                  ) : (
                    <div className="candidate-list__thumb-placeholder">
                      후보 {candidate.candidate_index ?? index + 1}
                    </div>
                  )}
                </div>
                <div className="candidate-list__body">
                  <span className="candidate-list__label">
                    {candidate.candidate_index ?? index + 1}위
                  </span>
                  <span className="candidate-list__time">
                    {formatTime(candidate.start_sec)}
                  </span>
                  <span className="candidate-list__appearance">
                    {candidate.appearance || appearance || '인상착의 일치'}
                  </span>
                </div>
              </button>
            </li>
          );
        })}
      </ul>
    </aside>
  );
}
