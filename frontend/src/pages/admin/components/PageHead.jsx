/** 관리자 뷰 공통 페이지 헤더 — breadcrumb + 제목 */
import { crumbOf } from "../navConfig"

export default function PageHead({ viewId, desc }) {
  const c = crumbOf[viewId] || []
  const title = c[c.length - 1] || ""
  const crumbParts = ["관리자 콘솔", ...c.slice(0, -1)]

  return (
    <>
      <div className="admin-crumb">
        {crumbParts.map((part, i) => (
          <span key={part}>
            {i > 0 && <b> › </b>}
            {part}
          </span>
        ))}
      </div>
      <div className="admin-page-title">{title}</div>
      {desc ? <div className="admin-page-desc">{desc}</div> : null}
    </>
  )
}
