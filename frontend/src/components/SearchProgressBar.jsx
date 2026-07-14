/** 검색·분석 진행 표시 — indeterminate ProgressBar */
import './SearchProgressBar.css';

export default function SearchProgressBar({
  label = '검색 중…',
  visible = false,
}) {
  if (!visible) return null;

  return (
    <div
      className="search-progress"
      role="status"
      aria-live="polite"
      aria-busy="true"
    >
      <div className="search-progress__label">{label}</div>
      <div className="search-progress__track" aria-hidden="true">
        <div className="search-progress__bar" />
      </div>
    </div>
  );
}
