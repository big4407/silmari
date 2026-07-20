/** 검색·분석 진행 표시 — 원형 스피너 */
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
      <div className="search-progress__spinner" aria-hidden="true" />
      <div className="search-progress__label">{label}</div>
    </div>
  );
}
