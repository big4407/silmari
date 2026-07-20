/**
 * 검색 이력 — 검색 요청 목록.
 *
 * GET /search 연동 (dev 구조).
 */
import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { fetchSearchHistory } from '../api/client';
import { useDetectionStore } from '../store/useDetectionStore';
import './SearchHistory.css';

function formatDateTime(iso) {
  if (!iso) return '-';
  return new Date(iso).toLocaleString('ko-KR', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function truncateText(text, max = 48) {
  if (!text) return '-';
  const trimmed = text.replace(/\s+/g, ' ').trim();
  if (trimmed.length <= max) return trimmed;
  return `${trimmed.slice(0, max)}…`;
}

function personLabel(item) {
  const name = item.person_name || '미상';
  if (item.person_age) return `${name} (${item.person_age}세)`;
  return name;
}

const SEARCH_TYPE_META = {
  1: { label: '문자 검색', modifier: 'message' },
  2: { label: '챗봇', modifier: 'chatbot' },
  3: { label: '자동 검색', modifier: 'auto' },
};

function searchTypeMeta(searchType) {
  return (
    SEARCH_TYPE_META[String(searchType)] || {
      label: '기타',
      modifier: 'unknown',
    }
  );
}

function isWithinPeriod(iso, period) {
  if (!iso || period === 'all') return true;
  const date = new Date(iso);
  const now = new Date();
  if (period === 'today') {
    return date.toDateString() === now.toDateString();
  }
  if (period === 'week') {
    const weekAgo = new Date(now);
    weekAgo.setDate(now.getDate() - 7);
    return date >= weekAgo;
  }
  return true;
}

export default function SearchHistory() {
  const navigate = useNavigate();
  const setActiveSearch = useDetectionStore((s) => s.setActiveSearch);

  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [keyword, setKeyword] = useState('');
  const [period, setPeriod] = useState('all');

  const loadHistory = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchSearchHistory({ limit: 100 });
      setItems(Array.isArray(data) ? data : []);
    } catch {
      setError('검색 이력을 불러오지 못했습니다.');
      setItems([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadHistory();
  }, [loadHistory]);

  const filteredItems = useMemo(() => {
    const q = keyword.trim().toLowerCase();

    return items.filter((item) => {
      if (!isWithinPeriod(item.created_at, period)) return false;
      if (!q) return true;

      const typeLabel = searchTypeMeta(item.search_type).label;
      const haystack = [
        typeLabel,
        item.person_name,
        item.region,
        item.alert_text,
        item.video_filename,
        item.description,
      ]
        .filter(Boolean)
        .join(' ')
        .toLowerCase();
      return haystack.includes(q);
    });
  }, [items, keyword, period]);

  const summary = useMemo(() => {
    const todayItems = items.filter((item) =>
      isWithinPeriod(item.created_at, 'today'),
    );
    return {
      total: items.length,
      today: todayItems.length,
    };
  }, [items]);

  const handleOpenResults = (item) => {
    setActiveSearch({
      alertText: item.alert_text || '',
      smsInfo: item.sms_info || {
        name: item.person_name,
        age: item.person_age,
      },
      region: item.region && item.region !== '-' ? item.region : null,
      searchResultId: item.id,
    });
    navigate('/search-results');
  };

  return (
    <div className="search-history">
      <header className="search-history__header">
        <h1>검색 이력</h1>
        <span className="search-history__count">
          {loading ? '불러오는 중…' : `총 ${filteredItems.length}건`}
        </span>
        <button
          type="button"
          className="search-history__refresh"
          onClick={loadHistory}
          disabled={loading}
        >
          새로고침
        </button>
      </header>

      <div className="search-history__panel">
        <div className="search-history__summary">
          <div className="search-history__stat-card">
            <span className="search-history__stat-label">전체 이력</span>
            <strong>{summary.total}</strong>
          </div>
          <div className="search-history__stat-card">
            <span className="search-history__stat-label">오늘 검색</span>
            <strong>{summary.today}</strong>
          </div>
        </div>

        <div className="search-history__toolbar">
          <input
            type="search"
            className="search-history__search"
            placeholder="이름·지역·안내문자 검색"
            value={keyword}
            onChange={(e) => setKeyword(e.target.value)}
            aria-label="검색 이력 필터"
          />
          <div
            className="search-history__period"
            role="tablist"
            aria-label="기간 필터"
          >
            {[
              { id: 'all', label: '전체' },
              { id: 'today', label: '오늘' },
              { id: 'week', label: '7일' },
            ].map((tab) => (
              <button
                key={tab.id}
                type="button"
                role="tab"
                aria-selected={period === tab.id}
                className={`search-history__period-btn${
                  period === tab.id ? ' search-history__period-btn--on' : ''
                }`}
                onClick={() => setPeriod(tab.id)}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>

        {error && <p className="search-history__error">{error}</p>}

        <div className="search-history__body">
          {!loading && !error && filteredItems.length === 0 && (
            <div className="search-history__empty">
              <p>저장된 검색 이력이 없습니다.</p>
              <p>대시보드에서 안내문자를 선택하거나 챗봇으로 검색해 보세요.</p>
              <Link to="/dashboard" className="search-history__cta">
                실종자 검색
              </Link>
            </div>
          )}

          {!error && filteredItems.length > 0 && (
            <div className="search-history__table-wrap">
              <table className="search-history__table">
                <thead>
                  <tr>
                    <th scope="col">검색 일시</th>
                    <th scope="col" className="search-history__col-type">
                      타입
                    </th>
                    <th scope="col">대상자</th>
                    <th scope="col">지역</th>
                    <th scope="col">인상착의</th>
                    <th scope="col" className="search-history__col-action">
                      결과
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {filteredItems.map((item) => {
                    const type = searchTypeMeta(item.search_type);
                    return (
                      <tr
                        key={item.id}
                        className="search-history__row"
                        onClick={() => handleOpenResults(item)}
                      >
                        <td>{formatDateTime(item.created_at)}</td>
                        <td className="search-history__col-type">
                          <span
                            className={`search-history__type-badge search-history__type-badge--${type.modifier}`}
                          >
                            {type.label}
                          </span>
                        </td>
                        <td>
                          <span>{personLabel(item)}</span>
                        </td>
                        <td>{item.region || '-'}</td>
                        <td title={item.description}>
                          {truncateText(item.description)}
                        </td>
                        <td className="search-history__col-action">
                          <button
                            type="button"
                            className="search-history__view-btn"
                            onClick={(e) => {
                              e.stopPropagation();
                              handleOpenResults(item);
                            }}
                          >
                            결과 보기
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
