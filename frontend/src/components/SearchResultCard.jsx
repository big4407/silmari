/** 검색 결과 카드 — 썸네일·신뢰도·구간 수, 클릭 시 상세·클립 재생 */
import ConfidenceBar from "./ConfidenceBar"
import "./SearchResultCard.css"

function formatTime(sec) {
  const min = Math.floor(sec / 60)
  const s = (sec % 60).toFixed(1)
  return min > 0 ? `${min}분 ${s}초` : `${s}초`
}

export default function SearchResultCard({ result, onClick, onDelete, deleting }) {
  const confidencePct = Math.round(result.best_confidence * 100)

  return (
    <article className={`search-card${deleting ? " search-card--deleting" : ""}`}>
      <div
        className="search-card__main"
        role="button"
        tabIndex={deleting ? -1 : 0}
        onClick={() => !deleting && onClick(result)}
        onKeyDown={(e) => {
          if (!deleting && (e.key === "Enter" || e.key === " ")) {
            e.preventDefault()
            onClick(result)
          }
        }}
      >
        <div className="search-card__img-wrap">
          <img
            src={result.thumbnail_url}
            alt={result.video_filename}
            className="search-card__img"
          />
          <button
            type="button"
            className="search-card__delete"
            aria-label="검색 결과 삭제"
            disabled={deleting}
            onClick={(e) => {
              e.stopPropagation()
              onDelete?.(result)
            }}
          >
            ×
          </button>
        </div>
        <div className="search-card__body">
          <p className="search-card__meta">
            <span>{result.region}</span>
            <span>{formatTime(result.best_timestamp_sec)}</span>
            <span>정확도 {confidencePct}%</span>
          </p>
          <p className="search-card__desc">{result.description || result.video_filename}</p>
          <ConfidenceBar value={result.best_confidence} label="신뢰도" />
        </div>
      </div>
    </article>
  )
}
