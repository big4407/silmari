/** 영상 내 인상착의 매칭 후보 목록 — 페이지네이션, 클릭 시 해당 클립 재생 */
import { useEffect, useRef, useState } from 'react';
import './DetectionCandidateList.css';

const DEFAULT_ITEMS_PER_PAGE = 5;

function formatTime(sec) {
  if (sec == null || Number.isNaN(sec)) return '-';
  const min = Math.floor(sec / 60);
  const s = (sec % 60).toFixed(1);
  return min > 0 ? `${min}분 ${s}초` : `${s}초`;
}

export default function DetectionCandidateList({
  candidates,
  activeIndex = 0,
  onSelect,
  appearance,
  itemsPerPage = DEFAULT_ITEMS_PER_PAGE,
}) {
  const total = candidates?.length ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / itemsPerPage));
  const [page, setPage] = useState(0);
  const listRef = useRef(null);

  // 선택된 후보(activeIndex)가 바뀌면 그 후보가 있는 페이지로 자동 이동
  // — 다른 곳(영상 재생 등)에서 선택이 바뀌었을 때도 목록이 따라간다.
  useEffect(() => {
    if (total === 0) return;
    const pageOfActive = Math.floor(activeIndex / itemsPerPage);
    setPage(Math.min(pageOfActive, totalPages - 1));
  }, [activeIndex, itemsPerPage, total, totalPages]);

  // 페이지가 바뀔 때마다 목록 스크롤을 맨 위로 되돌린다 — 이전 페이지에서
  // 스크롤을 내려놓은 상태로 다음/이전을 누르면 새 페이지의 아래쪽부터
  // 보이는 게 혼란스러워서.
  useEffect(() => {
    listRef.current?.scrollTo({ top: 0 });
  }, [page]);

  if (!total) {
    return (
      <aside className="candidate-list candidate-list--empty">
        <h3>탐지 후보</h3>
        <p className="candidate-list__empty-msg">
          이 영상에서 인상착의에 해당하는 후보가 없습니다.
        </p>
      </aside>
    );
  }

  const pageStart = page * itemsPerPage;
  const pagedCandidates = candidates.slice(pageStart, pageStart + itemsPerPage);

  return (
    <aside className="candidate-list">
      <header className="candidate-list__header">
        <h3>탐지 후보</h3>
        <span className="candidate-list__count">{total}명</span>
      </header>
      {appearance && (
        <p className="candidate-list__filter">
          인상착의: <strong>{appearance}</strong>
        </p>
      )}
      <ul className="candidate-list__items" ref={listRef}>
        {pagedCandidates.map((candidate, localIndex) => {
          const index = pageStart + localIndex;
          const isActive = index === activeIndex;

          return (
            <li key={candidate.filename || index}>
              <button
                type="button"
                className={`candidate-list__item${
                  isActive ? ' candidate-list__item--active' : ''
                }`}
                onClick={() => onSelect?.(index)}
                aria-pressed={isActive}
              >
                <div className="candidate-list__thumb-wrap">
                  {candidate.thumbnail_url ? (
                    <img
                      src={candidate.thumbnail_url}
                      alt={`후보 ${candidate.candidate_index ?? index + 1}`}
                      className="candidate-list__thumb"
                    />
                  ) : (
                    <div className="candidate-list__thumb-placeholder">
                      후보 {candidate.candidate_index ?? index + 1}
                    </div>
                  )}
                </div>
                <div className="candidate-list__body">
                  <span className="candidate-list__label">
                    {candidate.candidate_index ?? index + 1}위
                  </span>
                  <span className="candidate-list__time">
                    {formatTime(candidate.start_sec)}
                  </span>
                  <span className="candidate-list__appearance">
                    {candidate.appearance || appearance || '인상착의 일치'}
                  </span>
                </div>
              </button>
            </li>
          );
        })}
      </ul>
      {totalPages > 1 && (
        <div className="candidate-list__pager">
          <button
            type="button"
            className="candidate-list__pager-btn"
            onClick={() => setPage((p) => Math.max(0, p - 1))}
            disabled={page <= 0}
          >
            이전
          </button>
          <span className="candidate-list__pager-label">
            {page + 1} / {totalPages}
          </span>
          <button
            type="button"
            className="candidate-list__pager-btn"
            onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
            disabled={page >= totalPages - 1}
          >
            다음
          </button>
        </div>
      )}
    </aside>
  );
}
