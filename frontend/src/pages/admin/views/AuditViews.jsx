/** 감사 로그 뷰 — 관리자·승인·로그인 이력 (목 UI) */
import PageHead from '../components/PageHead';
import { StatValue, TableEmptyRow } from '../components/EmptyState';

export function AuditAdminView() {
  return (
    <>
      <PageHead
        viewId="audit-admin"
        desc="관리자가 수행한 모든 작업(데이터 수정·삭제·보내기 등)을 시간순으로 기록합니다. 행위자·대상·결과를 추적할 수 있습니다."
      />
      <div className="admin-toolbar">
        <input placeholder="행위자·대상 검색" disabled />
        <select disabled>
          <option>전체 유형</option>
        </select>
        <input type="date" disabled />
        <div className="admin-spacer" />
        <button type="button" className="admin-btn" disabled>
          로그보내기
        </button>
      </div>
      <div className="admin-card admin-table-wrap">
        <table>
          <thead>
            <tr>
              <th>시각</th>
              <th>행위자</th>
              <th>유형</th>
              <th>대상 · 변경 내용</th>
              <th>결과</th>
              <th>IP</th>
            </tr>
          </thead>
          <tbody>
            <TableEmptyRow colSpan={6} />
          </tbody>
        </table>
      </div>
      <p className="admin-footnote">
        ※ 가입 승인·권한 변경은 보안 감사를 위해 <b>승인·권한변경 이력</b>에서
        별도 추적합니다.
      </p>
    </>
  );
}

export function AuditApprovalView() {
  return (
    <>
      <PageHead
        viewId="audit-approval"
        desc="가입 승인과 역할(권한) 변경을 별도로 추적합니다. 누가 누구에게 어떤 권한을 부여했는지가 보안 감사의 핵심입니다."
      />
      <div className="admin-toolbar">
        <input placeholder="처리자·대상 검색" disabled />
        <select disabled>
          <option>전체 유형</option>
        </select>
        <input type="date" disabled />
        <div className="admin-spacer" />
        <button type="button" className="admin-btn" disabled>
          로그보내기
        </button>
      </div>
      <div className="admin-card admin-table-wrap">
        <table>
          <thead>
            <tr>
              <th>시각</th>
              <th>처리자</th>
              <th>유형</th>
              <th>대상</th>
              <th>변경 (전 → 후)</th>
              <th>사유</th>
            </tr>
          </thead>
          <tbody>
            <TableEmptyRow colSpan={6} />
          </tbody>
        </table>
      </div>
    </>
  );
}

export function AuditLoginView() {
  return (
    <>
      <PageHead
        viewId="audit-login"
        desc="로그인 성공·실패와 접근 기록입니다. 이상 접근(반복 실패·비정상 IP)을 탐지합니다. 활성 세션 관리는 회원 관리에서 처리합니다."
      />
      <div className="admin-stat-grid">
        <div className="admin-stat admin-stat--green">
          <div className="admin-label">오늘 로그인</div>
          <StatValue />
        </div>
        <div className="admin-stat admin-stat--amber">
          <div className="admin-label">실패</div>
          <StatValue />
        </div>
        <div className="admin-stat admin-stat--red">
          <div className="admin-label">이상 접근</div>
          <StatValue />
        </div>
        <div className="admin-stat">
          <div className="admin-label">활성 사용자</div>
          <StatValue />
        </div>
      </div>
      <div className="admin-card admin-table-wrap">
        <table>
          <thead>
            <tr>
              <th>시각</th>
              <th>계정</th>
              <th>구분</th>
              <th>결과</th>
              <th>IP</th>
              <th>기기</th>
            </tr>
          </thead>
          <tbody>
            <TableEmptyRow colSpan={6} />
          </tbody>
        </table>
      </div>
    </>
  );
}
