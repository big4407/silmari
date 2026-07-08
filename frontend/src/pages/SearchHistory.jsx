/**
 * 검색 이력 — CCTV 분석 세션 목록.
 *
 * GET /api/v1/detection-results/history 연동.
 * 행 클릭 시 해당 안내문자 컨텍스트로 검색 결과 페이지 이동.
 */
import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { API_BASE, fetchSearchHistory } from '../api/client';
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

function formatConfidence(value) {
  if (value == null || Number.isNaN(value)) return '-';
  return `${(value * 100).toFixed(1)}%`;
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

function confidenceLevel(value) {
  if (value == null || Number.isNaN(value)) {
    return { label: '-', className: 'search-history__badge--muted' };
  }
  const pct = value * 100;
  if (pct >= 80) {
    return { label: formatConfidence(value), className: 'search-history__badge--high' };
  }
  if (pct >= 60) {
    return { label: formatConfidence(value), className: 'search-history__badge--mid' };
  }
  return { label: formatConfidence(value), className: 'search-history__badge--low' };
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

      const haystack = [
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
    const confidences = items
      .map((item) => item.best_confidence)
      .filter((v) => v != null && !Number.isNaN(v));
    const avgConfidence = confidences.length
      ? confidences.reduce((sum, v) => sum + v, 0) / confidences.length
      : null;

    return {
      total: items.length,
      today: todayItems.length,
      avgConfidence:
        avgConfidence != null ? `${(avgConfidence * 100).toFixed(1)}%` : '-',
    };
  }, [items]);

  const handleOpenResults = (item) => {
    setActiveSearch({
      alertText: item.alert_text,
      smsInfo: item.sms_info || {
        name: item.person_name,
        age: item.person_age,
      },
      region: item.region && item.region !== '-' ? item.region : null,
      searchResultId: item.id,
      analysisSummary: {
        totalDetections: item.candidate_count ?? item.clips?.length ?? 1,
        videoFilename: item.video_filename,
        noMatch: false,
        demoMode: false,
      },
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
            <span className="search-history__stat-label">오늘 분석</span>
            <strong>{summary.today}</strong>
          </div>
          <div className="search-history__stat-card">
            <span className="search-history__stat-label">평균 신뢰도</span>
            <strong>{summary.avgConfidence}</strong>
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
          <div className="search-history__period" role="tablist" aria-label="기간 필터">
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

        {!loading && !error && filteredItems.length === 0 && (
          <div className="search-history__empty">
            <p>저장된 검색 이력이 없습니다.</p>
            <p>탐지 결과가 저장되면 이력이 여기에 표시됩니다.</p>
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
                  <th scope="col">대상자</th>
                  <th scope="col">지역</th>
                  <th scope="col">안내문자</th>
                  <th scope="col">영상</th>
                  <th scope="col">신뢰도</th>
                  <th scope="col" className="search-history__col-action">
                    결과
                  </th>
                </tr>
              </thead>
              <tbody>
                {filteredItems.map((item) => {
                  const thumbUrl = item.thumbnail_url?.startsWith('http')
                    ? item.thumbnail_url
                    : `${API_BASE}${item.thumbnail_url}`;

                  return (
                    <tr
                      key={item.id}
                      className="search-history__row"
                      onClick={() => handleOpenResults(item)}
                    >
                      <td>{formatDateTime(item.created_at)}</td>
                      <td>
                        <div className="search-history__person">
                          {item.thumbnail_url && (
                            <img
                              src={thumbUrl}
                              alt=""
                              className="search-history__thumb"
                            />
                          )}
                          <span>{personLabel(item)}</span>
                        </div>
                      </td>
                      <td>{item.region || '-'}</td>
                      <td title={item.alert_text}>
                        {truncateText(item.alert_text)}
                      </td>
                      <td title={item.video_filename}>
                        {truncateText(item.video_filename, 24)}
                      </td>
                      <td>
                        {(() => {
                          const badge = confidenceLevel(item.best_confidence);
                          return (
                            <span
                              className={`search-history__badge ${badge.className}`}
                            >
                              {badge.label}
                            </span>
                          );
                        })()}
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
  );
}
