/** 데이터 관리 뷰 — 코드·검증·보내기·보존 정책 (목 UI) */
import PageHead from '../components/PageHead';
import EmptyState, { TableEmptyRow } from '../components/EmptyState';

export function DataCodesView() {
  return (
    <>
      <PageHead
        viewId="data-codes"
        desc="지역(행정구역)·역할·검색유형 등 시스템 기준 코드를 관리합니다. region 계층과 각 코드 테이블이 대상입니다."
      />
      <div className="admin-cols">
        <div className="admin-card">
          <div className="admin-card-h">
            행정구역 (region){' '}
            <button type="button" className="admin-btn admin-btn--sm" disabled>
              코드 추가
            </button>
          </div>
          <div className="admin-card-b">
            <EmptyState message="등록된 행정구역이 없습니다." />
            <p
              style={{
                fontSize: 12,
                color: 'var(--admin-ink-3)',
                marginTop: 10,
              }}
            >
              parent_code 기반 계층(self-FK). 영상·검색이 이 코드를 참조합니다.
            </p>
          </div>
        </div>
        <div className="admin-card">
          <div className="admin-card-h">코드 그룹</div>
          <div
            className="admin-card-b admin-table-wrap"
            style={{ paddingTop: 6 }}
          >
            <table>
              <thead>
                <tr>
                  <th>그룹</th>
                  <th>코드값</th>
                  <th>참조</th>
                </tr>
              </thead>
              <tbody>
                <TableEmptyRow
                  colSpan={3}
                  message="코드 그룹을 불러오지 못했습니다."
                />
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </>
  );
}

export function DataValidateView() {
  return (
    <>
      <PageHead
        viewId="data-validate"
        desc="테이블 간 참조 무결성과 데이터 정합성을 검사합니다. 고아 레코드·끊긴 계층·잘못된 코드값을 탐지합니다."
      />
      <div className="admin-toolbar">
        <button type="button" className="admin-btn admin-btn--primary" disabled>
          정합성 검사 실행
        </button>
        <span className="admin-pill admin-pill--muted">마지막 검사 —</span>
        <div className="admin-spacer" />
        <button type="button" className="admin-btn" disabled>
          오류 리포트 다운로드
        </button>
      </div>
      <div className="admin-card admin-table-wrap">
        <table>
          <thead>
            <tr>
              <th>검사 항목</th>
              <th>대상</th>
              <th>검사 내용</th>
              <th>결과</th>
              <th style={{ textAlign: 'right' }} />
            </tr>
          </thead>
          <tbody>
            <TableEmptyRow
              colSpan={5}
              message="정합성 검사를 실행하면 결과가 표시됩니다."
            />
          </tbody>
        </table>
      </div>
    </>
  );
}

export function DataExportView() {
  return (
    <>
      <PageHead
        viewId="data-export"
        desc="조회·검색·통계 데이터를 표준 형식으로 일괄보냅니다.보내기 이력은 감사 로그에 기록됩니다."
      />
      <div className="admin-card admin-mb">
        <div className="admin-card-h">새보내기</div>
        <div className="admin-card-b">
          <div className="admin-form-row">
            <div className="admin-fld">
              <label>데이터 종류</label>
              <select disabled>
                <option>데이터 종류를 선택하세요</option>
              </select>
            </div>
            <div className="admin-fld">
              <label>기간</label>
              <input type="date" disabled />
            </div>
            <div className="admin-fld">
              <label>형식</label>
              <select disabled>
                <option>CSV</option>
              </select>
            </div>
            <div className="admin-fld" style={{ flex: '0 0 auto' }}>
              <label>&nbsp;</label>
              <button
                type="button"
                className="admin-btn admin-btn--primary"
                disabled
              >
                보내기
              </button>
            </div>
          </div>
        </div>
      </div>
      <div className="admin-card admin-table-wrap">
        <div className="admin-card-h">최근보내기</div>
        <table>
          <thead>
            <tr>
              <th>일시</th>
              <th>데이터</th>
              <th>기간</th>
              <th>형식</th>
              <th>행 수</th>
              <th>요청자</th>
              <th style={{ textAlign: 'right' }} />
            </tr>
          </thead>
          <tbody>
            <TableEmptyRow colSpan={7} />
          </tbody>
        </table>
      </div>
    </>
  );
}

export function DataRetentionView() {
  return (
    <>
      <PageHead
        viewId="data-retention"
        desc="데이터 유형별 보존 기간과 자동 삭제 정책을 설정합니다. 영상·임베딩 등 민감·대용량 데이터의 만료 관리가 핵심입니다."
      />
      <div className="admin-card admin-table-wrap">
        <div className="admin-card-h">
          보존 정책{' '}
          <button
            type="button"
            className="admin-btn admin-btn--sm admin-btn--primary"
            disabled
          >
            정책 저장
          </button>
        </div>
        <table>
          <thead>
            <tr>
              <th>데이터 유형</th>
              <th>테이블/저장소</th>
              <th>보존 기간</th>
              <th>만료 처리</th>
              <th>현재 보관량</th>
              <th>상태</th>
            </tr>
          </thead>
          <tbody>
            <TableEmptyRow
              colSpan={6}
              message="보존 정책이 설정되지 않았습니다."
            />
          </tbody>
        </table>
      </div>
      <p className="admin-footnote">
        ※ 영상 삭제 시 Chroma 임베딩도 함께 삭제돼야 정합성이 유지됩니다.
      </p>
    </>
  );
}
