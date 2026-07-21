/** 대시보드 재난·안내문자 카드 — 선택 시 탐지 컨텍스트로 사용 */
import './AlertMessageCard.css';
import { isCaseWriter } from '../api/client';

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

export default function AlertMessageCard({
  alert,
  index,
  selected,
  onClick,
  onAddCase,
  addingCase = false,
}) {
  if (!alert) {
    return (
      <div className="alert-card alert-card--empty">
        <span>안내문자 {index + 1}</span>
      </div>
    );
  }

  const resolved = alert.case_status === '3';
  // 케이스가 아직 없는 문자(case_status == null)만 관리자·수사관에게 추가 버튼 노출.
  const canAddCase = alert.case_status == null && isCaseWriter();

  const preview =
    alert.msg_cn?.length > 100
      ? `${alert.msg_cn.slice(0, 100)}…`
      : alert.msg_cn;

  return (
    <div className="alert-card-wrap">
      <button
        type="button"
        className={`alert-card ${selected ? 'alert-card--selected' : ''} ${
          resolved ? 'alert-card--resolved' : ''
        } ${canAddCase ? 'alert-card--addable' : ''}`}
        onClick={() => !resolved && onClick?.(alert)}
        disabled={resolved}
        title={resolved ? '이미 처리 완료된 케이스입니다' : undefined}
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
          {resolved && <span className="alert-card__resolved-badge">완료</span>}
        </div>
      </button>
      {canAddCase && (
        <button
          type="button"
          className="alert-card__add-btn"
          onClick={(e) => {
            e.stopPropagation();
            if (!addingCase) onAddCase?.(alert);
          }}
          disabled={addingCase}
          title="이 문자를 실종자관리에 추가"
        >
          {addingCase ? '추가 중…' : '+ 실종자관리 추가'}
        </button>
      )}
    </div>
  );
}
