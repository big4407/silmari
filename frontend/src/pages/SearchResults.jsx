/**
 * 탐지 결과 목록·상세·클립 재생.
 *
 * [모드] activeSearch(방금 분석) 또는 DB 이력(fetchSearchResults)
 * [UI] MissingPersonSidebar + ClipSequencePlayer + SearchResultCard
 */
import { useEffect, useMemo, useState } from "react"
import { Link } from "react-router-dom"
import { fetchSearchResults, deleteSearchResult, deleteAllSearchResults, API_BASE } from "../api/client"
import { useDetectionStore } from "../store/useDetectionStore"
import SearchResultCard from "../components/SearchResultCard"
import ClipSequencePlayer from "../components/ClipSequencePlayer"
import MissingPersonSidebar from "../components/MissingPersonSidebar"
import "./SearchResults.css"

function resultToSidebar(data) {
  if (!data) return null
  return {
    name: data.person_name,
    age: data.person_age,
    gender: data.sms_info?.gender,
    clothes: data.sms_info?.clothes,
    location: data.region,
    missing_date: null,
    photo_url: null,
    alertText: data.alert_text,
  }
}

function buildSidebarPerson(activeSearch, selectedResult, firstResult) {
  if (activeSearch) {
    const sms = activeSearch.smsInfo || {}
    return {
      name: sms.name || "미상",
      age: sms.age,
      gender: sms.gender,
      clothes: sms.clothes,
      location: activeSearch.region || null,
      missing_date: null,
      photo_url: null,
      alertText: activeSearch.alertText,
    }
  }

  return resultToSidebar(selectedResult || firstResult)
}

export default function SearchResults() {
  const { selectedPerson, selectedRegion, activeSearch } = useDetectionStore()
  const [results, setResults] = useState([])
  const [loading, setLoading] = useState(false)
  const [selectedResult, setSelectedResult] = useState(null)
  const [error, setError] = useState(null)
  const [deletingId, setDeletingId] = useState(null)
  const [clearingAll, setClearingAll] = useState(false)

  const searchParams = useMemo(() => {
    const params = {}
    if (activeSearch?.alertText) {
      params.alert_text = activeSearch.alertText
    } else if (selectedPerson?.name) {
      params.person_name = selectedPerson.name
    }
    if (selectedRegion && selectedRegion !== "전국") {
      params.region = selectedRegion
    }
    return params
  }, [activeSearch?.alertText, selectedPerson?.name, selectedRegion])

  const sidebarPerson = useMemo(
    () => buildSidebarPerson(activeSearch, selectedResult, results[0]),
    [activeSearch, selectedResult, results],
  )

  const loadResults = async () => {
    setLoading(true)
    setError(null)
    setSelectedResult(null)
    try {
      const data = await fetchSearchResults(searchParams)
      setResults(data)
    } catch {
      setError("검색 결과를 불러오지 못했습니다.")
      setResults([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadResults()
  }, [activeSearch?.alertText, selectedPerson?.name, selectedRegion])

  const handleDeleteResult = async (result) => {
    if (!window.confirm("이 검색 결과를 삭제할까요?")) return

    setDeletingId(result.id)
    setError(null)
    try {
      await deleteSearchResult(result.id)
      setResults(prev => prev.filter(r => r.id !== result.id))
      if (selectedResult?.id === result.id) {
        setSelectedResult(null)
      }
    } catch {
      setError("검색 결과를 삭제하지 못했습니다.")
    } finally {
      setDeletingId(null)
    }
  }

  const handleDeleteAll = async () => {
    if (!window.confirm(`표시된 검색 결과 ${results.length}건을 모두 삭제할까요?`)) return

    setClearingAll(true)
    setError(null)
    try {
      await deleteAllSearchResults(searchParams)
      setResults([])
      setSelectedResult(null)
    } catch {
      setError("검색 결과를 삭제하지 못했습니다.")
    } finally {
      setClearingAll(false)
    }
  }

  const clipsWithFullUrl = selectedResult?.clips?.map(c => ({
    ...c,
    url: c.url.startsWith("http") ? c.url : `${API_BASE}${c.url}`,
  }))

  const contextLabel = activeSearch
    ? "현재 안내문자"
    : selectedPerson
      ? `${selectedPerson.name} 검색`
      : null

  return (
    <div className="search-page">
      <header className="search-page__header">
        <h1>검색결과</h1>
        {contextLabel && (
          <span className="search-page__person">
            {contextLabel}
            {selectedRegion !== "전국" ? ` · ${selectedRegion}` : ""}
          </span>
        )}
        {results.length > 0 && !selectedResult && (
          <button
            type="button"
            className="search-page__clear-btn"
            onClick={handleDeleteAll}
            disabled={clearingAll || loading}
          >
            {clearingAll ? "삭제 중..." : "전체 삭제"}
          </button>
        )}
      </header>

      <div className="search-page__body">
        <main className="search-page__main">
          {!activeSearch && !selectedPerson && (
            <p className="search-page__hint">
              CCTV 분석을 실행하면 해당 안내문자의 검색 결과가 표시됩니다.
              <Link to="/cctv"> CCTV 분석</Link>
            </p>
          )}

          {loading && <p className="search-page__status">불러오는 중...</p>}
          {error && <p className="search-page__error">{error}</p>}

          {!loading && !error && !selectedResult && (
            results.length === 0 ? (
              <div className="search-page__empty">
                <p>아직 검색 결과가 없습니다.</p>
                <p>CCTV 영상을 업로드해 분석을 실행해주세요.</p>
                <Link to="/cctv">CCTV 분석</Link>
              </div>
            ) : (
              <div className="search-grid">
                {results.map(r => (
                  <SearchResultCard
                    key={r.id}
                    result={{
                      ...r,
                      thumbnail_url: r.thumbnail_url.startsWith("http")
                        ? r.thumbnail_url
                        : `${API_BASE}${r.thumbnail_url}`,
                    }}
                    onClick={setSelectedResult}
                    onDelete={handleDeleteResult}
                    deleting={deletingId === r.id || clearingAll}
                  />
                ))}
              </div>
            )
          )}

          {selectedResult && (
            <ClipSequencePlayer
              clips={clipsWithFullUrl}
              onBack={() => setSelectedResult(null)}
            />
          )}
        </main>

        <MissingPersonSidebar person={sidebarPerson} />
      </div>
    </div>
  )
}
