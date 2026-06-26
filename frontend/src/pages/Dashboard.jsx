import { useCallback, useEffect, useMemo, useState } from "react"
import { useNavigate } from "react-router-dom"
import MapDrilldown from "../components/MapDrilldown"
import AlertMessageCard from "../components/AlertMessageCard"
import { fetchDisasterAlerts } from "../api/client"
import { useDetectionStore } from "../store/useDetectionStore"
import { filterAlertsByRegion, resolveAlertMapFocus } from "../utils/regionMatch"
import { findRegionByName } from "../utils/regionSearch"
import "./Dashboard.css"

function toYmd(dateStr) {
  if (!dateStr) return undefined
  return dateStr.replace(/-/g, "")
}

const ALERTS_STORAGE_KEY = "silmari_alerts_cache"

function loadAlertsFromSession() {
  try {
    const raw = sessionStorage.getItem(ALERTS_STORAGE_KEY)
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

function saveAlertsToSession(items) {
  try {
    sessionStorage.setItem(ALERTS_STORAGE_KEY, JSON.stringify({ items, ts: Date.now() }))
  } catch {
    // sessionStorage unavailable
  }
}

function regionFilterLabel(mapFilter) {
  if (!mapFilter || mapFilter.level === "nation") return null
  if (mapFilter.level === "gu") return `${mapFilter.sidoLabel} ${mapFilter.label}`
  return mapFilter.label
}

/** 시스템/설정 오류는 사용자에게 그대로 노출하지 않음 */
function resolveFetchNotice(error) {
  if (!error) return null
  const text = error.toLowerCase()
  if (
    text.includes("api 키")
    || text.includes("url이 설정")
    || text.includes("service_key")
    || text.includes("인증키")
  ) {
    return null
  }
  if (text.includes("한도") || text.includes("limit")) {
    return {
      tone: "warning",
      message:
        "오늘 조회 한도에 도달했습니다. 내일 다시 시도하거나, 이전에 조회한 결과가 있으면 목록에서 확인해 주세요.",
    }
  }
  return {
    tone: "info",
    message: "안내문자를 불러오지 못했습니다. 잠시 후 「안내문자 조회」를 다시 눌러 주세요.",
  }
}

export default function Dashboard() {
  const navigate = useNavigate()
  const {
    loading, selectedAlert, alertList,
    startDate, endDate, contentKeyword,
    setAlertList, setLoading, setSelectedAlert, setSelectedRegion,
    setStartDate, setEndDate, setContentKeyword, setAlertText, setActiveSearch,
  } = useDetectionStore()

  const [apiError, setApiError] = useState(null)
  const [hasSearched, setHasSearched] = useState(false)
  const [mapFilter, setMapFilter] = useState({ level: "nation" })
  const [mapFocus, setMapFocus] = useState(null)
  const [regionQuery, setRegionQuery] = useState("")
  const [regionSearchError, setRegionSearchError] = useState(null)
  const isDefaultQuery = !startDate && !endDate && !contentKeyword.trim()
  const keywordTrimmed = contentKeyword.trim()

  const filteredAlerts = useMemo(
    () => filterAlertsByRegion(alertList, mapFilter),
    [alertList, mapFilter],
  )

  const regionLabel = regionFilterLabel(mapFilter)
  const fetchNotice = resolveFetchNotice(apiError)

  const loadList = async ({ refresh = false, cacheOnly = false } = {}) => {
    if (refresh) setHasSearched(true)
    setLoading(true)
    setApiError(null)
    try {
      const params = {
        num_of_rows: 100,
        missing_only: true,
      }
      if (refresh) params.force_refresh = true
      if (cacheOnly) params.cache_only = true
      const crtDt = toYmd(startDate)
      const endDt = toYmd(endDate)
      if (crtDt) params.crt_dt = crtDt
      if (endDt) params.end_dt = endDt
      if (keywordTrimmed) params.keyword = keywordTrimmed

      const data = await fetchDisasterAlerts(params)
      if (data.error) {
        console.warn("[alerts]", data.error)
        setApiError(data.error)
        setAlertList([])
        return
      }
      if (data.hint && (!data.items || data.items.length === 0)) {
        setAlertList([])
        return
      }
      const items = data.items || []
      setAlertList(items)
      if (items.length > 0) saveAlertsToSession(items)
    } catch (e) {
      console.error("안내문자 목록 불러오기 실패", e)
      setAlertList([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    const saved = loadAlertsFromSession()
    if (saved?.items?.length) {
      setAlertList(saved.items)
      return
    }
    loadList({ cacheOnly: true })
  }, [])

  const handleSearch = () => loadList({ refresh: true })

  const handleMapRegionSelect = useCallback((filter) => {
    setMapFilter(filter || { level: "nation" })
    setSelectedRegion(regionFilterLabel(filter) || "전국")
  }, [setSelectedRegion])

  const handleRegionSearch = (e) => {
    e.preventDefault()
    const query = regionQuery.trim()
    if (!query) {
      setRegionSearchError(null)
      return
    }
    const focus = findRegionByName(query)
    if (!focus) {
      setRegionSearchError("일치하는 지역을 찾을 수 없습니다. 시·도 또는 구·군 이름을 확인해 주세요.")
      return
    }
    setRegionSearchError(null)
    setMapFocus({ ...focus, key: Date.now() })
  }

  const handleSelectAlert = (alert) => {
    setSelectedAlert(alert)
    setAlertText(alert.msg_cn)
    setSelectedRegion(alert.rcptn_rgn_nm || "전국")
    setActiveSearch({
      alertText: alert.msg_cn,
      smsInfo: {},
      region: alert.rcptn_rgn_nm || null,
    })
    const focus = resolveAlertMapFocus(alert.rcptn_rgn_nm)
    if (focus) {
      setMapFocus({ ...focus, key: Date.now() })
    }
  }

  return (
    <div className="page">
      <section className="filter-panel" aria-label="조회 조건">
        <div className="filter-panel__head">
          <h2 className="filter-panel__title">조회 조건</h2>
          {regionLabel && (
            <span className="filter-panel__chip">지역 · {regionLabel}</span>
          )}
          {keywordTrimmed && (
            <span className="filter-panel__chip">내용 · {keywordTrimmed}</span>
          )}
        </div>

        <div className="filter-panel__body">
          <div className="filter-panel__group">
            <span className="filter-panel__label">기간</span>
            <div className="filter-panel__dates">
              <input
                id="search-start-date"
                type="date"
                value={startDate}
                onChange={e => setStartDate(e.target.value)}
                aria-label="시작일"
              />
              <span className="filter-panel__sep">~</span>
              <input
                id="search-end-date"
                type="date"
                value={endDate}
                onChange={e => setEndDate(e.target.value)}
                aria-label="종료일"
              />
            </div>
          </div>

          <div className="filter-panel__group">
            <span className="filter-panel__label">문자 내용</span>
            <input
              type="search"
              className="filter-panel__keyword"
              placeholder="예) 실종, 홍길동, 검은 점퍼"
              value={contentKeyword}
              onChange={(e) => setContentKeyword(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault()
                  handleSearch()
                }
              }}
              aria-label="안내문자 내용 검색"
            />
          </div>

          <form className="filter-panel__group" onSubmit={handleRegionSearch}>
            <span className="filter-panel__label">지역</span>
            <div className="filter-panel__region">
              <input
                type="text"
                placeholder="시·도·구·군 검색"
                value={regionQuery}
                onChange={(e) => {
                  setRegionQuery(e.target.value)
                  if (regionSearchError) setRegionSearchError(null)
                }}
                aria-label="지역명 검색"
              />
              <button type="submit" className="filter-panel__btn filter-panel__btn--sub">
                지도 이동
              </button>
            </div>
          </form>

          <div className="filter-panel__actions">
            <button
              type="button"
              className="filter-panel__btn filter-panel__btn--primary"
              onClick={handleSearch}
              disabled={loading}
            >
              {loading ? "조회 중…" : "안내문자 조회"}
            </button>
          </div>
        </div>

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
              <span className="sidebar__count-badge">{filteredAlerts.length}건</span>
            )}
          </div>

          {selectedAlert && (
            <div className="sidebar__actions">
              <button
                type="button"
                className="sidebar__action-btn sidebar__action-btn--primary"
                onClick={() => navigate("/cctv")}
              >
                CCTV 분석
              </button>
              <button
                type="button"
                className="sidebar__action-btn"
                onClick={() => navigate("/search-results")}
              >
                검색결과 보기
              </button>
            </div>
          )}

          {loading && (
            <p className="sidebar-hint">조회 중… (과거 기간은 시간이 걸릴 수 있습니다)</p>
          )}
          {!loading && filteredAlerts.length > 0 && isDefaultQuery && (
            <p className="sidebar-hint">
              기본 조회 (최근 90일)
              {regionLabel && ` · ${regionLabel}`}
            </p>
          )}
          {!loading && filteredAlerts.length > 0 && !isDefaultQuery && (
            <p className="sidebar-hint">
              {[
                startDate || endDate ? "기간 지정" : null,
                keywordTrimmed ? `내용 "${keywordTrimmed}"` : null,
                regionLabel ? `지역 ${regionLabel}` : null,
              ].filter(Boolean).join(" · ") || "조회 조건 적용"}
            </p>
          )}
          {fetchNotice && (
            <p className={`sidebar-notice sidebar-notice--${fetchNotice.tone}`}>
              {fetchNotice.message}
            </p>
          )}

          <div className="sidebar__body">
            {!loading && filteredAlerts.length === 0 ? (
              <div className="sidebar-empty-state">
                <div className="sidebar-empty-state__icon" aria-hidden="true">
                  <svg width="40" height="40" viewBox="0 0 48 48" fill="none">
                    <rect x="6" y="10" width="36" height="28" rx="3" stroke="currentColor" strokeWidth="2" />
                    <path d="M14 20h20M14 26h14" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                  </svg>
                </div>
                <p className="sidebar-empty-state__title">
                  {alertList.length > 0 && regionLabel
                    ? `${regionLabel} 지역 결과 없음`
                    : hasSearched || startDate || endDate || keywordTrimmed
                      ? "조건에 맞는 안내문자가 없습니다"
                      : "표시할 안내문자가 없습니다"}
                </p>
                <p className="sidebar-empty-state__message">
                  {alertList.length > 0 && regionLabel
                    ? "지도에서 다른 지역을 선택해 보세요."
                    : hasSearched || startDate || endDate || keywordTrimmed
                      ? "기간·내용·지역을 넓혀 다시 조회해 보세요."
                      : "조건을 설정한 뒤 상단 「안내문자 조회」를 눌러 주세요."}
                </p>
              </div>
            ) : (
              <div className="sidebar__list">
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
            )}
          </div>
        </aside>
      </div>
    </div>
  )
}
