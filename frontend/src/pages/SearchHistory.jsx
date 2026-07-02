/** 검색 이력 페이지 — 현재 플레이스홀더 (향후 GET /api/v1/detection-results/history 연동 예정) */
import './SearchHistory.css';

export default function SearchHistory() {
  // TODO: detection-results/history API 연동 후 목록·필터 UI 구현
  return (
    <div className="search-history">
      <div className="search-history__placeholder">
        <h1>검색 이력</h1>
        <p>준비 중입니다.</p>
      </div>
    </div>
  );
}
