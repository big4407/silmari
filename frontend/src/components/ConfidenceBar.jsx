/** YOLO 탐지 신뢰도 시각화 바 — SearchResultCard 에서 사용 */
import "./ConfidenceBar.css"

export default function ConfidenceBar({ value, label }) {
  const pct = Math.round((value || 0) * 100)
  return (
    <div className="confidence-bar">
      {label && <span className="confidence-bar__label">{label}</span>}
      <div className="confidence-bar__track">
        <div className="confidence-bar__fill" style={{ width: `${pct}%` }} />
      </div>
      <span className="confidence-bar__pct">{pct}%</span>
    </div>
  )
}
