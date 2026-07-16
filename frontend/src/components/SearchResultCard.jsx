/** 검색 결과 카드 — 썸네일·신뢰도·구간 수, 클릭 시 상세·클립 재생 */
import './SearchResultCard.css';

function formatTime(sec) {
  const min = Math.floor(sec / 60);
  const s = (sec % 60).toFixed(1);
  return min > 0 ? `${min}분 ${s}초` : `${s}초`;
}

export default function SearchResultCard({
  result,
  onClick,
  onDelete,
  deleting,
}) {
  console.log('SearchResultCard result:', result);
  const hasThumb = Boolean(result.thumbnail_url);
  const pathParts = result.video_path?.split(/[\\/]/) || [];
  const cctvNo = pathParts.at(-2);
  const rankLabel =
    result.rank === 1
      ? '1st'
      : result.rank === 2
        ? '2nd'
        : result.rank === 3
          ? '3rd'
          : null;
  return (
    <article
      className={`search-card${deleting ? ' search-card--deleting' : ''}`}
    >
      <div
        className="search-card__main"
        role="button"
        tabIndex={deleting ? -1 : 0}
        onClick={() => !deleting && onClick(result)}
        onKeyDown={(e) => {
          if (!deleting && (e.key === 'Enter' || e.key === ' ')) {
            e.preventDefault();
            onClick(result);
          }
        }}
      >
        <div className="search-card__img-wrap">
          {hasThumb ? (
            <img
              src={result.thumbnail_url}
              alt={result.video_filename || result.person_name}
              className="search-card__img"
            />
          ) : (
            <div className="search-card__img search-card__img--placeholder">
              {result.person_name || '검색'}
            </div>
          )}
          {rankLabel && (
            <span
              className={`search-card__rank search-card__rank--${result.rank}`}
            >
              {rankLabel}
            </span>
          )}
        </div>
        <div className="search-card__body">
          <p className="search-card__video-info">
            {cctvNo} · {result.recorded_at}
          </p>
          <p className="search-card__meta">
            <span>{result.video_region || result.region}</span>
            <span>
              {result.best_timestamp_sec != null
                ? formatTime(result.best_timestamp_sec)
                : '-'}
            </span>
          </p>
          <p className="search-card__desc">
            {result.description || result.video_filename}
          </p>
        </div>
      </div>
    </article>
  );
}
