/** API 테스트 뷰 공통 페이지 헤더 — breadcrumb + 제목 */
export default function DevPageHead({ title, desc }) {
  return (
    <>
      <div className="admin-crumb">
        API 테스트
        {title ? (
          <>
            <b> › </b>
            {title}
          </>
        ) : null}
      </div>
      {title ? <div className="admin-page-title">{title}</div> : null}
      {desc ? <div className="admin-page-desc">{desc}</div> : null}
    </>
  );
}
