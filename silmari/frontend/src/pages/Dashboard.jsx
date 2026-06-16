import { useCallback, useEffect, useMemo, useState } from "react"
import { useNavigate } from "react-router-dom"
import MapDrilldown from "../components/MapDrilldown"
import AlertMessageCard from "../components/AlertMessageCard"
import ChatbotWidget from "../components/ChatbotWidget"
import { fetchDisasterAlerts } from "../api/client"
import { useDetectionStore } from "../store/useDetectionStore"
import { filterAlertsByRegion, resolveAlertMapFocus } from "../utils/regionMatch"
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
  const [apiWarning, setApiWarning] = useState(null)
  const [mapFilter, setMapFilter] = useState({ level: "nation" })
  const [mapFocus, setMapFocus] = useState(null)
  const isDefaultQuery = !startDate && !endDate

  const filteredAlerts = useMemo(
    () => filterAlertsByRegion(alertList, mapFilter),
    [alertList, mapFilter],
  )

  const regionLabel = regionFilterLabel(mapFilter)

  const loadList = async ({ refresh = false, cacheOnly = false } = {}) => {
    setLoading(true)
    setApiError(null)
    if (refresh) setApiWarning(null)
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
      if (data.warning) {
        setApiWarning(data.warning)
      } else if (data.api_calls_used) {
        setApiWarning(
          `이번 검색에서 외부 API ${data.api_calls_used}회 사용됨 (일일 한도 1,000회 · 문자 1건당 1회가 아님)`,
        )
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
      const ageH = Math.floor((Date.now() - (saved.ts || 0)) / 3600000)
      if (ageH >= 1) {
        setApiWarning(`브라우저에 저장된 조회 결과입니다 (${ageH}시간 전). 최신 데이터는 검색 버튼을 눌러주세요.`)
      }
      return
    }
    loadList({ cacheOnly: true })
  }, [])

  const handleSearch = () => loadList({ refresh: true })

  const handleMapRegionSelect = useCallback((filter) => {
    setMapFilter(filter || { level: "nation" })
    setSelectedRegion(regionFilterLabel(filter) || "전국")
  }, [setSelectedRegion])

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
      <div className="main-area">
        <MapDrilldown
          onRegionSelect={handleMapRegionSelect}
          focusTarget={mapFocus}
          alerts={alertList}
        />

        <aside className="sidebar">
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
          {apiWarning && (
            <p className="sidebar-warning">{apiWarning}</p>
          )}
          {apiError && (
            <p className="sidebar-error">{apiError}</p>
          )}
          {!loading && !apiError && filteredAlerts.length === 0 && (
            <p className="sidebar-error">
              {alertList.length > 0 && regionLabel
                ? `${regionLabel} 지역 실종 안내문자가 없습니다. 지도에서 다른 지역을 선택해 보세요.`
                : startDate || endDate
                  ? "해당 기간에 실종 안내문자가 없습니다. 검색기간·지역을 넓혀 보세요."
                  : "아래 검색 버튼을 눌러 실종 안내문자를 조회하세요."}
            </p>
          )}
          {filteredAlerts.length > 0 && (
            <p className="sidebar-count">
              실종 안내문자 {filteredAlerts.length}건
              {regionLabel && alertList.length !== filteredAlerts.length
                ? ` (${regionLabel})`
                : ""}
            </p>
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
        </aside>
      </div>

      <div className="search-bar">
        <div className="date-range">
          <label>검색기간</label>
          <input type="date" value={startDate} onChange={e => setStartDate(e.target.value)} />
          <span className="date-separator">~</span>
          <input type="date" value={endDate} onChange={e => setEndDate(e.target.value)} />
          {regionLabel && (
            <span className="date-separator">| {regionLabel}</span>
          )}
        </div>
        <button className="search-btn" onClick={handleSearch} disabled={loading}>
          {loading ? "검색 중..." : "검색"}
        </button>
        {selectedAlert && (
          <>
            <button
              className="search-btn search-btn--primary"
              onClick={() => navigate("/cctv")}
            >
              CCTV 분석
            </button>
            <button
              className="search-btn search-btn--primary"
              onClick={() => navigate("/search-results")}
            >
              검색결과 보기
            </button>
          </>
        )}
      </div>

      <ChatbotWidget />
    </div>
  )
}
