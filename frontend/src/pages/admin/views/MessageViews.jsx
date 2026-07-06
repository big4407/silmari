/** 안내문자 관리 뷰 — 목록·인상착의 파싱 검수 (목 UI) */
import PageHead from '../components/PageHead';
import EmptyState, { TableEmptyRow } from '../components/EmptyState';
import { ReportRow } from '../components/MessageBody';
import { useState, useEffect } from 'react';
import { getMessageList } from '../../../api/client';

// 문자 목록을 보여주는 함수
export function ReportsView() {
  const PAGE_SIZE = 10; // 한 페이지에 보여줄 문자 수
  const [reports, setReports] = useState([]);
  const [page, setPage] = useState(1); // 현재 페이지
  const [total, setTotal] = useState(0); // 총 문자 수

  const totalPages = Math.ceil(total / PAGE_SIZE);

  // 실제로 보일 페이지 배열을 계산하는 함수, 첫 페이지와 마지막 페이지는 항상 보이므로 그 외만 처리
  const getPageNumbers = () => {
    const maxVisible = 5; // 가운데 보일 페이지 수, 이외의 페이지는 ... 처리

    let start = Math.max(1, page - Math.floor(maxVisible / 2));
    let end = start + maxVisible - 1;

    if (end > totalPages) {
      end = totalPages;
      start = Math.max(1, end - maxVisible + 1);
    }

    return Array.from({ length: end - start + 1 }, (_, index) => start + index);
  };

  const pageNumbers = getPageNumbers();

  const renderPageButton = (
    pageNumber,
    paginationButtonClass = 'admin-btn',
  ) => (
    <button
      key={pageNumber}
      type="button"
      className={paginationButtonClass}
      onClick={() => setPage(pageNumber)}
    >
      {pageNumber}
    </button>
  );

  useEffect(() => {
    async function fetchReports() {
      try {
        const data = await getMessageList({
          page,
          per_page: PAGE_SIZE,
        });
        setReports(data.items);
        setTotal(data.total);
      } catch (error) {
        setReports([]);
        setTotal(0);
      }
    }

    fetchReports();
  }, [page, PAGE_SIZE]);

  return (
    <>
      <PageHead
        viewId="reports"
        desc="수집된 재난문자 중 실종 관련 안내문자를 조회합니다. 선택한 문자는 인상착의 파싱 검수와 CCTV 검색의 입력으로 사용됩니다."
      />

      <div className="admin-toolbar">
        <input placeholder="내용·지역 검색" disabled />
        <select disabled>
          <option>긴급단계 전체</option>
        </select>
        <select disabled>
          <option>재해구분 전체</option>
        </select>
        <input type="date" disabled />
        <div className="admin-spacer" />
        <span className="admin-pill admin-pill--muted">실종 관련만 표시</span>
      </div>

      <div className="admin-card admin-table-wrap">
        <table>
          <thead>
            <tr>
              <th>일련번호</th>
              <th>수신 일시</th>
              <th>수신 지역</th>
              <th>긴급단계</th>
              <th>내용</th>
              <th>분류 상태</th>
            </tr>
          </thead>
          <tbody>
            {reports.length === 0 ? (
              <TableEmptyRow colSpan={6} />
            ) : (
              reports.map((report) => (
                <ReportRow key={report.sn} report={report} />
              ))
            )}
          </tbody>
        </table>
      </div>

      <div className="admin-pagination">
        <button
          className="admin-btn"
          type="button"
          disabled={page === 1}
          onClick={() => setPage((prev) => prev - 1)}
        >
          이전
        </button>

        {pageNumbers[0] > 1 && (
          <>
            {renderPageButton(1)}
            {pageNumbers[0] > 2 && <span>...</span>}
          </>
        )}

        {pageNumbers.map((pageNumber) =>
          renderPageButton(
            pageNumber,
            page === pageNumber ? 'admin-btn admin-btn--primary' : 'admin-btn',
          ),
        )}

        {pageNumbers[pageNumbers.length - 1] < totalPages && (
          <>
            {pageNumbers[pageNumbers.length - 1] < totalPages - 1 && (
              <span>...</span>
            )}
            {renderPageButton(totalPages)}
          </>
        )}

        <button
          className="admin-btn"
          type="button"
          disabled={page === totalPages || totalPages === 0}
          onClick={() => setPage((prev) => prev + 1)}
        >
          다음
        </button>
      </div>

      <p className="admin-footnote">
        ※ 재난문자 원천 데이터(<code>message</code>)에서 재해구분·키워드로 실종
        관련 건만 필터링해 표시합니다.
      </p>
    </>
  );
}

export function ParseReviewView() {
  return (
    <>
      <PageHead
        viewId="parse-review"
        desc="안내문자에서 LLM이 추출한 인상착의를 사람이 검토·보정합니다. 확정된 인상착의가 CCTV 검색 조건으로 사용됩니다."
      />
      <div className="admin-toolbar">
        <select disabled>
          <option>검수 대기 우선</option>
        </select>
        <select disabled>
          <option>전체 지역</option>
        </select>
        <div className="admin-spacer" />
        <span className="admin-pill admin-pill--muted">검수 대기 —</span>
        <span className="admin-pill admin-pill--muted">확정 —</span>
      </div>
      <div className="admin-cols admin-cols--equal">
        <div className="admin-card">
          <div className="admin-card-h">안내문자 원문</div>
          <div className="admin-card-b">
            <div className="admin-text-block admin-text-block--empty">
              검수할 안내문자를 선택하세요.
            </div>
          </div>
        </div>
        <div className="admin-card">
          <div className="admin-card-h">LLM 파싱 결과 — 검토·수정</div>
          <div className="admin-card-b">
            <EmptyState message="선택된 안내문자의 파싱 결과가 없습니다." />
          </div>
        </div>
      </div>
    </>
  );
}
