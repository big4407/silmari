/** 대시보드 재난·안내문자 카드 — 선택 시 탐지 컨텍스트로 사용 */
import './AlertMessageCard.css';

function formatDate(crtDt) {
  if (!crtDt) return '';
  const s = String(crtDt);
  if (s.length >= 8) {
    return `${s.slice(0, 4)}-${s.slice(4, 6)}-${s.slice(6, 8)}`;
  }
  return s;
}

function tagVariant(name) {
  if (!name) return 'default';
  if (/실종|긴급|수색/.test(name)) return 'urgent';
  if (/안전|예방/.test(name)) return 'info';
  return 'default';
}

export default function AlertMessageCard({ alert, index, selected, onClick }) {
  if (!alert) {
    return (
      <div className="alert-card alert-card--empty">
        <span>안내문자 {index + 1}</span>
      </div>
    );
  }

  const preview =
    alert.msg_cn?.length > 100
      ? `${alert.msg_cn.slice(0, 100)}…`
      : alert.msg_cn;

  return (
    <button
      type="button"
      className={`alert-card ${selected ? 'alert-card--selected' : ''}`}
      onClick={() => onClick?.(alert)}
    >
      <div className="alert-card__head">
        <span className="alert-card__index">#{index + 1}</span>
        <span className="alert-card__date">
          {formatDate(alert.crt_dt || alert.reg_ymd)}
        </span>
      </div>
      {(alert.emrg_step_nm || alert.dst_se_nm) && (
        <div className="alert-card__meta">
          {alert.emrg_step_nm && (
            <span
              className={`alert-card__tag alert-card__tag--${tagVariant(alert.emrg_step_nm)}`}
            >
              {alert.emrg_step_nm}
            </span>
          )}
          {alert.dst_se_nm && (
            <span
              className={`alert-card__tag alert-card__tag--${tagVariant(alert.dst_se_nm)}`}
            >
              {alert.dst_se_nm}
            </span>
          )}
        </div>
      )}
      <p className="alert-card__text">{preview}</p>
      <div className="alert-card__footer">
        <span className="alert-card__region">
          {alert.rcptn_rgn_nm || '지역 미상'}
        </span>
      </div>
    </button>
  );
}
