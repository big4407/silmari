import { Link } from 'react-router-dom';

/** 관리자 콘솔 ↔ API 테스트 전환 (상단 점선 박스) */
export default function AdminConsoleSwitch({ mode }) {
  return (
    <div className="admin-switch-group">
      {mode === 'dev' ? (
        <span className="admin-switch-link admin-switch-link--active" aria-current="page">
          API 테스트
        </span>
      ) : (
        <Link to="/dev" className="admin-switch-link">
          API 테스트
        </Link>
      )}
      {mode === 'admin' ? (
        <span className="admin-switch-link admin-switch-link--active" aria-current="page">
          관리자
        </span>
      ) : (
        <Link to="/admin" className="admin-switch-link">
          관리자
        </Link>
      )}
    </div>
  );
}
