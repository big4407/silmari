/** 회원 관리 뷰 — 가입 승인 대기·전체 회원 (목 UI, /api/v1/admin 연동 예정) */
import PageHead from '../components/PageHead';
import { TableEmptyRow } from '../components/EmptyState';

export function MembersPendingView() {
  return (
    <>
      <PageHead
        viewId="members-pending"
        desc="가입을 신청한 사용자를 검토하고 승인하거나 반려합니다. 승인 시 역할을 함께 지정하세요."
      />
      <div className="admin-toolbar">
        <input placeholder="이름·이메일·소속 검색" disabled />
        <select disabled>
          <option>전체 소속</option>
        </select>
        <div className="admin-spacer" />
        <button type="button" className="admin-btn" disabled>
          선택 반려
        </button>
        <button type="button" className="admin-btn admin-btn--primary" disabled>
          선택 승인
        </button>
      </div>
      <div className="admin-card admin-table-wrap">
        <table>
          <thead>
            <tr>
              <th style={{ width: 34 }}>
                <input type="checkbox" aria-label="전체 선택" disabled />
              </th>
              <th>이름</th>
              <th>이메일</th>
              <th>소속</th>
              <th>신청 역할</th>
              <th>신청일</th>
              <th>대기</th>
              <th style={{ textAlign: 'right' }}>처리</th>
            </tr>
          </thead>
          <tbody>
            <TableEmptyRow colSpan={8} />
          </tbody>
        </table>
      </div>
    </>
  );
}

export function MembersAllView() {
  return (
    <>
      <PageHead
        viewId="members-all"
        desc="전체 회원을 조회하고 역할·상태·활성 세션을 관리합니다. 행을 선택하면 상세에서 권한 변경과 세션 강제 종료가 가능합니다."
      />
      <div className="admin-toolbar">
        <input placeholder="이름·이메일 검색" disabled />
        <select disabled>
          <option>전체 역할</option>
        </select>
        <select disabled>
          <option>전체 상태</option>
        </select>
        <div className="admin-spacer" />
        <button type="button" className="admin-btn" disabled>
          CSV보내기
        </button>
      </div>
      <div className="admin-card admin-table-wrap">
        <table>
          <thead>
            <tr>
              <th>이름</th>
              <th>이메일</th>
              <th>소속</th>
              <th>역할</th>
              <th>상태</th>
              <th>활성 세션</th>
              <th>최근 로그인</th>
              <th style={{ textAlign: 'right' }}>관리</th>
            </tr>
          </thead>
          <tbody>
            <TableEmptyRow colSpan={8} />
          </tbody>
        </table>
      </div>
    </>
  );
}
