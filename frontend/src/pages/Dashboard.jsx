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

export default function Dashboard() {
  const navigate = useNavigate()
  const {
    loading, selectedAlert, alertList,
    startDate, endDate,
    setAlertList, setLoading, setSelectedAlert, setSelectedRegion,
    setStartDate, setEndDate, setAlertText, setActiveSearch,
  } = useDetectionStore()

  const [apiError, setApiError] = useState(null)
  const [mapFilter, setMapFilter] = useState({ level: "nation" })
  const [mapFocus, setMapFocus] = useState(null)
  const [regionQuery, setRegionQuery] = useState("")
  const [regionSearchError, setRegionSearchError] = useState(null)
  const isDefaultQuery = !startDate && !endDate

  const filteredAlerts = useMemo(
    () => filterAlertsByRegion(alertList, mapFilter),
    [alertList, mapFilter],
  )

  const regionLabel = regionFilterLabel(mapFilter)

  const loadList = async ({ refresh = false, cacheOnly = false } = {}) => {
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

      const data = await fetchDisasterAlerts(params)
      if (data.error) {
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
    const focus = findRegionByName(regionQuery)
    if (!focus) {
      setRegionSearchError("일치하는 지역을 찾을 수 없습니다.")
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
          {isDefaultQuery && !loading && (
            <p className="sidebar-hint">
              기본 조회 (최근 90일)
              {regionLabel && ` · ${regionLabel}`}
            </p>
          )}
          {regionLabel && !isDefaultQuery && (
            <p className="sidebar-hint">지역 필터 · {regionLabel}</p>
          )}
          {apiError && (
            <p className="sidebar-error">{apiError}</p>
          )}
          {!loading && !apiError && filteredAlerts.length === 0 && (
            <div className="sidebar-empty-state">
              <div className="sidebar-empty-state__icon" aria-hidden="true">
                <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
                  <rect x="6" y="10" width="36" height="28" rx="3" stroke="currentColor" strokeWidth="2" />
                  <path d="M14 20h20M14 26h14M14 32h10" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                </svg>
              </div>
              <h3 className="sidebar-empty-state__title">
                {alertList.length > 0 && regionLabel
                  ? `${regionLabel} 지역 결과 없음`
                  : startDate || endDate
                    ? "해당 기간 결과 없음"
                    : "조회된 안내문자가 없습니다"}
              </h3>
              <p className="sidebar-empty-state__message">
                {alertList.length > 0 && regionLabel
                  ? "지도에서 다른 지역을 선택해 보세요."
                  : startDate || endDate
                    ? "기간·지역 조건을 넓혀 다시 조회해 보세요."
                    : "아래 순서대로 실종 안내문자를 조회할 수 있습니다."}
              </p>
              <ol className="sidebar-empty-state__steps">
                <li>
                  <span className="sidebar-empty-state__step-num">1</span>
                  <div>
                    <strong>조회 조건 설정</strong>
                    <span>상단에서 기간·지역 입력</span>
                  </div>
                </li>
                <li>
                  <span className="sidebar-empty-state__step-num">2</span>
                  <div>
                    <strong>안내문자 조회</strong>
                    <span>「안내문자 조회」 버튼 클릭</span>
                  </div>
                </li>
                <li>
                  <span className="sidebar-empty-state__step-num">3</span>
                  <div>
                    <strong>항목 선택</strong>
                    <span>목록에서 안내문자 선택 후 분석</span>
                  </div>
                </li>
              </ol>
            </div>
          )}

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
        </aside>
      </div>
    </div>
  )
}
