/** 안내문자 관리 뷰 — 목록·인상착의 파싱 검수 (목 UI) */
import PageHead from '../components/PageHead';
import EmptyState, { TableEmptyRow } from '../components/EmptyState';
import Pagination from '../components/Pagination';
import { adminPinnedPaginationStyle } from '../components/adminTableUtils';
import { ReportRow } from '../components/MessageBody';
import { useState, useEffect } from 'react';
import { getMessageList } from '../../../api/client';

// 문자 목록을 보여주는 함수
export function ReportsView() {
  const PAGE_SIZE = 10; // 한 페이지에 보여줄 문자 수 — 행이 4개 열(SN/일시/지역/
  // 내용 미리보기)에 내용 칸이 길어질 수 있는 텍스트 위주 행이라 10줄 유지
  const [reports, setReports] = useState([]);
  const [page, setPage] = useState(1); // 현재 페이지
  const [total, setTotal] = useState(0); // 총 문자 수
  const [content, setContent] = useState(''); // 내용 검색어
  const [region, setRegion] = useState(''); // 지역 검색어
  const [startDate, setStartDate] = useState(''); // 검색 시작일
  const [endDate, setEndDate] = useState(''); // 검색 종료일
  const [orderBy, setOrderBy] = useState('latest'); // 정렬 기준

  // 실제 API에 전달되는 검색 조건
  const [search, setSearch] = useState({
    content: '',
    region: '',
    startDate: null,
    endDate: null,
    orderBy: 'latest',
  });

  const handleSearch = () => {
    setPage(1); // 첫 페이지부터 검색
    setSearch({
      content: content,
      region: region,
      startDate: startDate || null,
      endDate: endDate || null,
      orderBy: orderBy,
    });
  };

  const totalPages = Math.ceil(total / PAGE_SIZE);

  useEffect(() => {
    async function fetchReports() {
      try {
        const data = await getMessageList({
          page,
          per_page: PAGE_SIZE,
          ...search,
          orderBy: orderBy,
        });
        setReports(data.items);
        setTotal(data.total);
      } catch (error) {
        setReports([]);
        setTotal(0);
      }
    }

    fetchReports();
  }, [page, search, orderBy]);

  return (
    <>
      <PageHead
        viewId="reports"
        desc="수집된 재난문자 중 실종 관련 안내문자를 조회합니다. 선택한 문자는 인상착의 파싱 검수와 CCTV 검색의 입력으로 사용됩니다."
      />

      <form
        className="admin-toolbar"
        onSubmit={(e) => {
          e.preventDefault();
          handleSearch();
        }}
      >
        <input
          placeholder="내용 검색"
          value={content}
          onChange={(e) => setContent(e.target.value)}
        />

        <input
          placeholder="지역 검색"
          value={region}
          onChange={(e) => setRegion(e.target.value)}
        />

        <span>기간</span>

        <input
          type="date"
          value={startDate}
          onChange={(e) => setStartDate(e.target.value)}
        />
        <span>-</span>
        <input
          type="date"
          value={endDate}
          onChange={(e) => setEndDate(e.target.value)}
        />

        <button type="submit" className="admin-btn admin-btn--primary">
          검색
        </button>

        <div className="admin-spacer" />
        <select
          value={orderBy}
          onChange={(e) => {
            setOrderBy(e.target.value);
          }}
        >
          <option value="latest">최신순</option>
          <option value="oldest">오래된 순</option>
        </select>
      </form>

      <div style={adminPinnedPaginationStyle(PAGE_SIZE)}>
        <div className="admin-card admin-table-wrap">
        <table>
          <thead>
            <tr>
              <th>일련번호</th>
              <th>수신 일시</th>
              <th>수신 지역</th>
              <th>내용</th>
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

      <Pagination
        page={page}
        totalPages={totalPages}
        total={total}
        onPageChange={setPage}
      />
      </div>

      <p className="admin-footnote">
        ※ 재난문자 원천 데이터(<code>message</code>)에서 재해구분·키워드로 실종
        관련 건만 필터링해 표시합니다.
      </p>
    </>
  );
}
