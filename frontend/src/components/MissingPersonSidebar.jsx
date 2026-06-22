import "./MissingPersonSidebar.css"

export default function MissingPersonSidebar({ person }) {
  if (!person) {
    return (
      <aside className="missing-sidebar">
        <h3>실종 신고 관련 내용</h3>
        <p className="missing-sidebar__empty">
          CCTV 분석을 실행하면 입력한 안내문자 정보가 여기에 표시됩니다.
        </p>
      </aside>
    )
  }

  return (
    <aside className="missing-sidebar">
      <h3>실종 신고 관련 내용</h3>
      <div className="missing-sidebar__body">
        {person.photo_url ? (
          <img src={person.photo_url} alt={person.name} className="missing-sidebar__photo" />
        ) : (
          <div className="missing-sidebar__photo-placeholder">사진 없음</div>
        )}
        <dl>
          {person.alertText && (
            <div>
              <dt>안내문자</dt>
              <dd className="missing-sidebar__alert">{person.alertText}</dd>
            </div>
          )}
          <div><dt>이름</dt><dd>{person.name || "-"}</dd></div>
          <div><dt>나이</dt><dd>{person.age ? `${person.age}세` : "-"}</dd></div>
          <div><dt>성별</dt><dd>{person.gender || "-"}</dd></div>
          <div><dt>인상착의</dt><dd>{person.clothes || "-"}</dd></div>
          <div><dt>실종지</dt><dd>{person.location || "-"}</dd></div>
          <div><dt>실종일</dt><dd>{person.missing_date || "-"}</dd></div>
        </dl>
      </div>
    </aside>
  )
}
