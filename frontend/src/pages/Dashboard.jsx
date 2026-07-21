/**
 * 메인 대시보드 — 지도 + 실종 안내문자 목록.
 *
 * [지도] MapDrilldown — 시·도/구·군 드릴다운, 지역별 문자 필터
 * [데이터] fetchMessages(/message) + sessionStorage 캐시
 * [액션] 문자 선택 → 실종자 검색(POST /search) → /search-results 이동
 */
import { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import MapDrilldown from '../components/MapDrilldown';
import AlertMessageCard from '../components/AlertMessageCard';
import SearchProgressBar from '../components/SearchProgressBar';
import {
  collectMessages,
  createCaseForMessage,
  createSearch,
  fetchMessages,
  getUserId,
  parseAlertMessage,
} from '../api/client';
import { useDetectionStore } from '../store/useDetectionStore';
import {
  filterAlertsByRegion,
  resolveAlertMapFocus,
} from '../utils/regionMatch';
import { findRegionByName } from '../utils/regionSearch';
import './Dashboard.css';

function resolveDateRange(startDate, endDate) {
  let start = startDate || undefined;
  let end = endDate || undefined;
  let swapped = false;

  if (start && end && start > end) {
    [start, end] = [end, start];
    swapped = true;
  }

  if (start || end) {
    return {
      start_date: start,
      end_date: end,
      hasUserRange: true,
      swapped,
    };
  }

  return {
    start_date: undefined,
    end_date: undefined,
    hasUserRange: false,
    swapped: false,
  };
}

function mapMessageToAlert(message) {
  const crtDt = message.crt_dt;
  let crt_dt = crtDt;
  if (crtDt && String(crtDt).includes('T')) {
    crt_dt = String(crtDt).slice(0, 10).replace(/-/g, '');
  }
  return {
    ...message,
    id: message.sn != null ? String(message.sn) : message.id,
    crt_dt,
  };
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

/** 안내문자 본문에서 인상착의 후보 텍스트 추출 (최대 100자).
 *
 * 우선순위:
 *   1) "인상착의:" 같은 명시적 라벨 뒤 텍스트 — 실제 실종 안내문자에서 가장
 *      흔하고 신뢰도 높은 패턴. 동사 없이 "회색 잠바, 검정 바지"처럼 나열만
 *      하는 경우가 많아서 2번 패턴으로는 못 잡는다.
 *   2) "착용/입고/입은/차림" 같은 동사 주변 텍스트
 *   3) (최후 수단) 본문 맨 앞 100자 — 위 두 패턴이 다 없을 때만. 보통 지역·
 *      기관명 등 서두라 인상착의와 무관할 수 있음을 감안해야 함.
 */
function extractClothingFromAlert(text) {
  if (!text) return null;
  const normalized = text.replace(/\s+/g, ' ').trim();

  const labelMatch = normalized.match(/인상착의\s*[:：]?\s*([^.。\n]{1,100})/);
  if (labelMatch) return labelMatch[1].trim().slice(0, 100);

  const wearMatch = normalized.match(
    /[^.。\n]{0,80}(?:착용|입고|입은|차림)[^.。\n]{0,40}/,
  );
  if (wearMatch) return wearMatch[0].slice(0, 100);

  return normalized.slice(0, 100);
}

/** 안내문자 식별키 — sn/id 타입 혼재(숫자·문자)여도 동일하게 비교 */
function alertKey(alert) {
  if (!alert) return '';
  const key = alert.sn ?? alert.id;
  return key == null ? '' : String(key);
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
    selectedRegion,
  } = useDetectionStore();

  const [apiError, setApiError] = useState(null);
  const [addingCaseKey, setAddingCaseKey] = useState(null);
  const [searchError, setSearchError] = useState(null);
  const [searchRunning, setSearchRunning] = useState(false);
  const [dateWarning, setDateWarning] = useState(null);
  const [emptyHint, setEmptyHint] = useState(null);
  const [mapFilter, setMapFilter] = useState({ level: 'nation' });
  const [mapFocus, setMapFocus] = useState(null);
  const [regionQuery, setRegionQuery] = useState('');
  const [regionSearchError, setRegionSearchError] = useState(null);
  const isDefaultQuery = !startDate && !endDate;

  const filteredAlerts = useMemo(() => {
    const list = filterAlertsByRegion(alertList, mapFilter);
    const key = alertKey(selectedAlert);
    // 문자 클릭으로 지도가 깊게 들어가며 필터가 좁혀져도
    // 선택한 카드가 목록에서 사라지지 않게 유지한다(선택 파란 하이라이트 유지).
    if (!key) return list;
    if (list.some((a) => alertKey(a) === key)) return list;
    const selected = alertList.find((a) => alertKey(a) === key);
    return selected ? [selected, ...list] : list;
  }, [alertList, mapFilter, selectedAlert]);

  const regionLabel = regionFilterLabel(mapFilter);

  const loadList = async ({ refresh = false, cacheOnly = false } = {}) => {
    setLoading(true);
    setApiError(null);
    setDateWarning(null);
    setEmptyHint(null);
    try {
      const range = resolveDateRange(startDate, endDate);
      const { start_date, end_date, hasUserRange, swapped } = range;

      if (swapped) {
        setDateWarning('시작일이 종료일보다 늦어 순서를 바꿔 조회했습니다.');
      }

      if (refresh) {
        try {
          await collectMessages({
            page_no: 1,
            num_of_rows: 100,
            ...(hasUserRange && start_date
              ? { crt_dt: start_date.replace(/-/g, '') }
              : {}),
          });
        } catch (collectError) {
          const detail = collectError.response?.data?.detail;
          setApiError(
            typeof detail === 'string'
              ? detail
              : '재난문자 수집에 실패했습니다. 저장된 목록을 조회합니다.',
          );
        }
      }

      const data = await fetchMessages({
        page: 1,
        per_page: 100,
        ...(hasUserRange ? { start_date, end_date } : {}),
        order_by: 'latest',
      });

      const items = (data.items || []).map(mapMessageToAlert);
      if (cacheOnly && items.length === 0) {
        setAlertList([]);
        return;
      }

      setAlertList(items);
      if (items.length > 0) saveAlertsToSession(items);
      else if (hasUserRange) {
        setEmptyHint('선택한 기간에 해당하는 실종 안내문자가 없습니다.');
      } else if (refresh) {
        setEmptyHint(
          '저장된 실종 안내문자가 없습니다. API 키·기간을 확인한 뒤 다시 조회해 보세요.',
        );
      }
    } catch (e) {
      console.error('안내문자 목록 불러오기 실패', e);
      setAlertList([]);
      setApiError('안내문자 목록을 불러오지 못했습니다.');
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
    const normalized = {
      ...alert,
      id: alert.sn != null ? String(alert.sn) : alert.id,
    };
    setSelectedAlert(normalized);
    setAlertText(normalized.msg_cn);
    setSelectedRegion(normalized.rcptn_rgn_nm || '전국');
    setSearchError(null);
    setActiveSearch({
      alertText: normalized.msg_cn,
      smsInfo: {},
      region: normalized.rcptn_rgn_nm || null,
    });
    // 문자 클릭은 지도 카메라만 이동시키고, 사이드바 목록 필터(mapFilter)는
    // 건드리지 않는다(applyFilter: false). 필터까지 같이 좁히면 클릭한 문자에
    // 따라 REGION_DATA 매칭 정밀도가 달라져(동/구/시도 단위 등) 다른 카드들이
    // 화면에서 무작위로 사라지는 것처럼 보였다(선택 파란 표시가 "일부만 되는"
    // 현상의 실제 원인).
    const focus = resolveAlertMapFocus(normalized.rcptn_rgn_nm);
    if (focus) {
      setMapFocus({ ...focus, key: Date.now(), applyFilter: false });
    }
  };

  // 케이스가 없는 문자(case_status == null)를 실종자관리로 등록 — 관리자·수사관 전용.
  // 반환된 문자로 목록·세션 캐시를 갱신해 버튼이 사라지고 카드가 케이스 보유
  // 상태로 바뀐다. 백엔드가 sn 기준 멱등이라 중복 클릭도 안전.
  const handleAddCase = async (alert) => {
    const key = alertKey(alert);
    if (!key || addingCaseKey) return;
    setAddingCaseKey(key);
    setApiError(null);
    try {
      const updated = await createCaseForMessage(alert.sn ?? alert.id);
      const nextList = alertList.map((a) =>
        alertKey(a) === key ? { ...a, case_status: updated.case_status } : a,
      );
      setAlertList(nextList);
      saveAlertsToSession(nextList);
    } catch (err) {
      setApiError(
        err?.response?.data?.detail || '실종자관리 추가에 실패했습니다.',
      );
    } finally {
      setAddingCaseKey(null);
    }
  };

  const handleRunMissingPersonSearch = async () => {
    if (!selectedAlert || searchRunning) return;

    const userId = getUserId();
    if (!userId) {
      setSearchError('로그인이 필요합니다.');
      navigate('/login');
      return;
    }

    setSearchRunning(true);
    setSearchError(null);

    try {
      const range = resolveDateRange(startDate, endDate);
      const region =
        (selectedRegion && selectedRegion !== '전국' ? selectedRegion : null) ||
        selectedAlert.rcptn_rgn_nm ||
        null;
      console.log('안내문자 원문:', selectedAlert.msg_cn);
      // 안내문자 본문은 라벨 없는 자유 서식이라("...노영찬씨(남,76세)를 찾습니다-
      // 163cm,60kg,파란색티,검정바지..." 식) 정규식만으론 한계가 있어 LLM으로
      // 구조화 추출한다. 호출 실패(네트워크·LLM 오류) 시에는 검색 자체가 막히지
      // 않도록 기존 정규식 추출로 폴백한다.
      let parsed = null;
      try {
        parsed = await parseAlertMessage(selectedAlert.msg_cn);
      } catch (parseErr) {
        console.error('안내문자 LLM 파싱 실패, 정규식으로 대체', parseErr);
      }

      const payload = {
        user_id: userId,
        message_sn: selectedAlert.sn || selectedAlert.id,
        missing_name: parsed?.missing_name ?? null,
        gender: parsed?.gender ?? null,
        age: parsed?.age ?? null,
        clothing:
          parsed?.clothing || extractClothingFromAlert(selectedAlert.msg_cn),
        missing_location: region ? region.slice(0, 20) : null,
        search_type: '1',
        ...(range.hasUserRange && range.start_date && range.end_date
          ? { start_date: range.start_date, end_date: range.end_date }
          : {}),
      };

      const result = await createSearch(payload);

      setActiveSearch({
        alertText: selectedAlert.msg_cn,
        smsInfo: {
          name: result.missing_name,
          age: result.age,
          gender: result.gender,
          clothes: result.clothing,
        },
        region: result.missing_location || region,
        searchResultId: result.id,
      });
      navigate('/search-results');
    } catch (e) {
      console.error('실종자 검색 요청 실패', e);
      const detail = e.response?.data?.detail;
      setSearchError(
        typeof detail === 'string'
          ? detail
          : '실종자 검색 요청에 실패했습니다.',
      );
    } finally {
      setSearchRunning(false);
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
              onClick={handleRunMissingPersonSearch}
              disabled={!selectedAlert || searchRunning || loading}
              title={
                selectedAlert
                  ? '선택한 안내문자로 CCTV 검색을 실행합니다'
                  : '실종 안내문자를 먼저 선택하세요'
              }
            >
              {searchRunning ? '검색 중…' : '실종자 검색'}
            </button>
            <button
              type="button"
              className="filter-panel__btn filter-panel__btn--secondary"
              onClick={handleSearch}
              disabled={loading || searchRunning}
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
              ? '기간을 비우고 안내문자 조회를 누르면 저장된 목록을 불러옵니다. 기간을 지정하면 해당 범위만 표시합니다.'
              : `총 ${alertList.length}건 · 지도에서 지역을 클릭하거나 검색해 필터할 수 있습니다.`}
        </p>

        {regionSearchError && (
          <p className="filter-panel__error">{regionSearchError}</p>
        )}
        {searchError && <p className="filter-panel__error">{searchError}</p>}
        {dateWarning && <p className="filter-panel__error">{dateWarning}</p>}

        <div className="filter-panel__progress">
          <SearchProgressBar
            visible={searchRunning}
            label="검색 중… CCTV 영상을 분석하고 있습니다."
          />
        </div>
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

          {!loading &&
            filteredAlerts.length > 0 &&
            !isDefaultQuery &&
            regionLabel && (
              <p className="sidebar-hint">지역 필터 · {regionLabel}</p>
            )}
          {apiError && <p className="sidebar-error">{apiError}</p>}
          {emptyHint && !apiError && (
            <p className="sidebar-hint sidebar-hint--warn">{emptyHint}</p>
          )}

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
                key={alertKey(alert) || i}
                alert={alert}
                index={i}
                selected={
                  Boolean(alertKey(alert)) &&
                  alertKey(selectedAlert) === alertKey(alert)
                }
                onClick={handleSelectAlert}
                onAddCase={handleAddCase}
                addingCase={addingCaseKey === alertKey(alert)}
              />
            ))}
          </div>
        </aside>
      </div>
    </div>
  );
}
