import "./AlertMessageCard.css"

function formatDate(crtDt) {
  if (!crtDt) return ""
  const s = String(crtDt)
  if (s.length >= 8) {
    return `${s.slice(0, 4)}-${s.slice(4, 6)}-${s.slice(6, 8)}`
  }
  return s
}

export default function AlertMessageCard({ alert, index, selected, onClick }) {
  if (!alert) {
    return (
      <div className="alert-card alert-card--empty">
        <span>안내문자 {index + 1}</span>
      </div>
    )
  }

  const preview = alert.msg_cn?.length > 80
    ? `${alert.msg_cn.slice(0, 80)}…`
    : alert.msg_cn

  return (
    <button
      type="button"
      className={`alert-card ${selected ? "alert-card--selected" : ""}`}
      onClick={() => onClick?.(alert)}
    >
      <div className="alert-card__label">안내문자 {index + 1}</div>
      <div className="alert-card__meta">
        {alert.emrg_step_nm && <span>{alert.emrg_step_nm}</span>}
        {alert.dst_se_nm && <span>{alert.dst_se_nm}</span>}
      </div>
      <p className="alert-card__text">{preview}</p>
      <div className="alert-card__footer">
        <span>{alert.rcptn_rgn_nm || "-"}</span>
        <span>{formatDate(alert.crt_dt || alert.reg_ymd)}</span>
      </div>
    </button>
  )
}
