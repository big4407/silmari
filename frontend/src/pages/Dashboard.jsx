/**
 * 메인 대시보드 — 지도 + 실종 안내문자 목록.
 *
 * [지도] MapDrilldown — 시·도/구·군 드릴다운, 지역별 문자 필터
 * [데이터] fetchDisasterAlerts(missing_only) + sessionStorage 캐시
 * [액션] 문자 선택 → alertText 저장 → /search-results 이동
 */
import { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import MapDrilldown from '../components/MapDrilldown';
import AlertMessageCard from '../components/AlertMessageCard';
import { fetchDisasterAlerts } from '../api/client';
import { useDetectionStore } from '../store/useDetectionStore';
import {
  filterAlertsByRegion,
  resolveAlertMapFocus,
} from '../utils/regionMatch';
import { findRegionByName } from '../utils/regionSearch';
import './Dashboard.css';

function toYmd(dateStr) {
  if (!dateStr) return undefined;
  return dateStr.replace(/-/g, '');
}

const ALERTS_STORAGE_KEY = 'silmari_alerts_cache';

function loadAlertsFromSession() {
  try {
    const raw = sessionStorage.getItem(ALERTS_STORAGE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

function saveAlertsToSession(items) {
  try {
    sessionStorage.setItem(
      ALERTS_STORAGE_KEY,
      JSON.stringify({ items, ts: Date.now() }),
    );
  } catch {
    // sessionStorage unavailable
  }
}

function regionFilterLabel(mapFilter) {
  if (!mapFilter || mapFilter.level === 'nation') return null;
  if (mapFilter.level === 'gu')
    return `${mapFilter.sidoLabel} ${mapFilter.label}`;
  return mapFilter.label;
}

export default function Dashboard() {
  const navigate = useNavigate();
  const {
    loading,
    selectedAlert,
    alertList,
    startDate,
    endDate,
    setAlertList,
    setLoading,
    setSelectedAlert,
    setSelectedRegion,
    setStartDate,
    setEndDate,
    setAlertText,
    setActiveSearch,
  } = useDetectionStore();

  const [apiError, setApiError] = useState(null);
  const [mapFilter, setMapFilter] = useState({ level: 'nation' });
  const [mapFocus, setMapFocus] = useState(null);
  const [regionQuery, setRegionQuery] = useState('');
  const [regionSearchError, setRegionSearchError] = useState(null);
  const isDefaultQuery = !startDate && !endDate;

  const filteredAlerts = useMemo(
    () => filterAlertsByRegion(alertList, mapFilter),
    [alertList, mapFilter],
  );

  const regionLabel = regionFilterLabel(mapFilter);

  const loadList = async ({ refresh = false, cacheOnly = false } = {}) => {
    setLoading(true);
    setApiError(null);
    try {
      const params = {
        num_of_rows: 100,
        missing_only: true,
      };
      if (refresh) params.force_refresh = true;
      if (cacheOnly) params.cache_only = true;
      const crtDt = toYmd(startDate);
      const endDt = toYmd(endDate);
      if (crtDt) params.crt_dt = crtDt;
      if (endDt) params.end_dt = endDt;

      const data = await fetchDisasterAlerts(params);
      if (data.error) {
        setApiError(data.error);
        setAlertList([]);
        return;
      }
      if (data.hint && (!data.items || data.items.length === 0)) {
        setAlertList([]);
        return;
      }
      const items = data.items || [];
      setAlertList(items);
      if (items.length > 0) saveAlertsToSession(items);
    } catch (e) {
      console.error('안내문자 목록 불러오기 실패', e);
      setAlertList([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const saved = loadAlertsFromSession();
    if (saved?.items?.length) {
      setAlertList(saved.items);
      return;
    }
    loadList({ cacheOnly: true });
  }, []);

  const handleSearch = () => loadList({ refresh: true });

  const handleMapRegionSelect = useCallback(
    (filter) => {
      setMapFilter(filter || { level: 'nation' });
      setSelectedRegion(regionFilterLabel(filter) || '전국');
    },
    [setSelectedRegion],
  );

  const handleRegionSearch = async (e) => {
    e.preventDefault();
    const focus = await findRegionByName(regionQuery);
    if (!focus) {
      setRegionSearchError('일치하는 지역을 찾을 수 없습니다.');
      return;
    }
    setRegionSearchError(null);
    setMapFocus({ ...focus, key: Date.now() });
  };

  const handleSelectAlert = (alert) => {
    setSelectedAlert(alert);
    setAlertText(alert.msg_cn);
    setSelectedRegion(alert.rcptn_rgn_nm || '전국');
    setActiveSearch({
      alertText: alert.msg_cn,
      smsInfo: {},
      region: alert.rcptn_rgn_nm || null,
    });
    const focus = resolveAlertMapFocus(alert.rcptn_rgn_nm);
    if (focus) {
      setMapFocus({ ...focus, key: Date.now() });
    }
  };

  return (
    <div className="page">
      <section className="filter-panel" aria-label="조회 조건">
        <div className="filter-panel__toolbar">
          <div className="filter-panel__title-col">
            <h2 className="filter-panel__title">조회 조건</h2>
          </div>

          <div className="filter-panel__fields">
            <div className="filter-panel__group filter-panel__group--period">
              <span className="filter-panel__label">기간</span>
              <div className="filter-panel__dates">
                <input
                  id="search-start-date"
                  type="date"
                  value={startDate}
                  onChange={(e) => setStartDate(e.target.value)}
                  aria-label="시작일"
                />
                <span className="filter-panel__sep">~</span>
                <input
                  id="search-end-date"
                  type="date"
                  value={endDate}
                  onChange={(e) => setEndDate(e.target.value)}
                  aria-label="종료일"
                />
              </div>
            </div>

            <form
              className="filter-panel__group filter-panel__group--region"
              onSubmit={handleRegionSearch}
            >
              <span className="filter-panel__label">지역</span>
              <div className="filter-panel__region">
                <input
                  type="text"
                  placeholder="시·도·구·군 검색"
                  value={regionQuery}
                  onChange={(e) => {
                    setRegionQuery(e.target.value);
                    if (regionSearchError) setRegionSearchError(null);
                  }}
                  aria-label="지역명 검색"
                />
                <button
                  type="submit"
                  className="filter-panel__btn filter-panel__btn--secondary"
                >
                  지도 이동
                </button>
              </div>
            </form>

            {regionLabel && (
              <span className="filter-panel__chip">지역 · {regionLabel}</span>
            )}
          </div>

          <div className="filter-panel__actions">
            <button
              type="button"
              className="filter-panel__btn filter-panel__btn--primary"
              onClick={handleSearch}
              disabled={loading}
            >
              {loading ? '조회 중…' : '안내문자 조회'}
            </button>
          </div>
        </div>

        <p
          className={`filter-panel__hint${loading ? ' filter-panel__hint--loading' : ''}`}
        >
          {loading
            ? '안내문자를 불러오는 중입니다.'
            : alertList.length === 0
              ? '기간·지역을 설정한 뒤 안내문자 조회를 실행하세요. 저장된 목록이 없으면 최근 90일 기준으로 조회합니다.'
              : `총 ${alertList.length}건 · 지도에서 지역을 클릭하거나 검색해 필터할 수 있습니다.`}
        </p>

        {regionSearchError && (
          <p className="filter-panel__error">{regionSearchError}</p>
        )}
      </section>

      <div className="main-area">
        <MapDrilldown
          onRegionSelect={handleMapRegionSelect}
          focusTarget={mapFocus}
          alerts={alertList}
        />

        <aside className="sidebar">
          <div className="sidebar__header">
            <h2 className="sidebar__title">실종 안내문자</h2>
            {filteredAlerts.length > 0 && (
              <span className="sidebar__count-badge">
                {filteredAlerts.length}건
              </span>
            )}
          </div>

          {selectedAlert && (
            <div className="sidebar__actions">
              <button
                type="button"
                className="sidebar__action-btn sidebar__action-btn--primary"
                onClick={() => navigate('/search-results')}
              >
                검색결과 보기
              </button>
            </div>
          )}

          {!loading && filteredAlerts.length > 0 && isDefaultQuery && (
            <p className="sidebar-hint">
              기본 조회 (최근 90일)
              {regionLabel && ` · ${regionLabel}`}
            </p>
          )}
          {!loading &&
            filteredAlerts.length > 0 &&
            !isDefaultQuery &&
            regionLabel && (
              <p className="sidebar-hint">지역 필터 · {regionLabel}</p>
            )}
          {apiError && <p className="sidebar-error">{apiError}</p>}

          <div className="sidebar__list">
            {!loading && filteredAlerts.length === 0 && (
              <div className="sidebar__empty">
                <div className="sidebar__empty-icon" aria-hidden="true">
                  <svg width="40" height="40" viewBox="0 0 24 24" fill="none">
                    <path
                      d="M20 4H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2zm0 4l-8 5-8-5V6l8 5 8-5v2z"
                      fill="currentColor"
                    />
                  </svg>
                </div>
                <p className="sidebar__empty-title">
                  표시할 안내문자가 없습니다
                </p>
                <p className="sidebar__empty-desc">
                  상단 <strong>안내문자 조회</strong>를 실행하거나 지도에서
                  지역을 선택하세요.
                </p>
              </div>
            )}
            {filteredAlerts.map((alert, i) => (
              <AlertMessageCard
                key={alert.id || i}
                alert={alert}
                index={i}
                selected={selectedAlert?.id === alert.id}
                onClick={handleSelectAlert}
              />
            ))}
          </div>
        </aside>
      </div>
    </div>
  );
}
