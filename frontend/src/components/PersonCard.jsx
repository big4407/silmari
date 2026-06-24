import "./PersonCard.css"

export default function PersonCard({ person, index, selected, onClick }) {
  if (!person) {
    return (
      <div className="person-card person-card--empty">
        <span>실종자 인상착의{index + 1}</span>
      </div>
    )
  }

  return (
    <div
      className={`person-card ${selected ? "person-card--selected" : ""}`}
      onClick={() => onClick?.(person)}
      role="button"
      tabIndex={0}
      onKeyDown={e => e.key === "Enter" && onClick?.(person)}
    >
      <div className="person-card__label">실종자 인상착의{index + 1}</div>
      {person.photo_url ? (
        <img src={person.photo_url} alt={person.name} className="person-card__photo" />
      ) : (
        <div className="person-card__photo-placeholder">사진 없음</div>
      )}
      <div className="person-card__info">
        <strong>{person.name}</strong>
        <span>{person.gender} · {person.age}세</span>
        <span className="person-card__clothes">{person.clothes || "인상착의 정보 없음"}</span>
        <span className="person-card__location">{person.location}</span>
      </div>
    </div>
  )
}
