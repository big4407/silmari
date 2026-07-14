/**
 * 탐지·검색 결과 목록·상세.
 *
 * [모드] activeSearch(선택한 검색 컨텍스트) 또는 DB 이력(fetchSearchResults → /search)
 */
import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  fetchSearchResults,
  fetchSearchResultDetail,
  deleteSearchResult,
  deleteAllSearchResults,
  API_BASE,
} from '../api/client';
import { useDetectionStore } from '../store/useDetectionStore';
import SearchResultCard from '../components/SearchResultCard';
import ClipSequencePlayer from '../components/ClipSequencePlayer';
import DetectionCandidateList from '../components/DetectionCandidateList';
import MissingPersonSidebar from '../components/MissingPersonSidebar';
import './SearchResults.css';

function resultToSidebar(data) {
  if (!data) return null;
  return {
    name: data.person_name,
    age: data.person_age,
    gender: data.sms_info?.gender,
    clothes: data.sms_info?.clothes,
    location: data.region,
    missing_date: null,
    photo_url: null,
    alertText: data.alert_text,
  };
}

function buildSidebarPerson(activeSearch, selectedResult, firstResult) {
  if (activeSearch) {
    const sms = activeSearch.smsInfo || {};
    return {
      name: sms.name || '미상',
      age: sms.age,
      gender: sms.gender,
      clothes: sms.clothes,
      location: activeSearch.region || null,
      missing_date: null,
      photo_url: null,
      alertText: activeSearch.alertText,
    };
  }

  return resultToSidebar(selectedResult || firstResult);
}

function thumbUrl(path) {
  if (!path) return '';

  if (path.startsWith('http')) {
    return path;
  }

  const normalizedPath = path.replace(/\\/g, '/');
  const dataIndex = normalizedPath.indexOf('/data/');

  if (dataIndex !== -1) {
    const relativePath = normalizedPath.slice(dataIndex + 6);
    return `${API_BASE}/media/${relativePath}`;
  }

  if (normalizedPath.startsWith('data/')) {
    return `${API_BASE}/media/${normalizedPath.slice(5)}`;
  }

  return `${API_BASE}/${normalizedPath.replace(/^\/+/, '')}`;
}

export default function SearchResults() {
  const { selectedPerson, selectedRegion, activeSearch } = useDetectionStore();
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [selectedResult, setSelectedResult] = useState(null);
  const [error, setError] = useState(null);
  const [deletingId, setDeletingId] = useState(null);
  const [clearingAll, setClearingAll] = useState(false);
  const [sortBy, setSortBy] = useState('confidence-desc');
  const [activeClipIndex, setActiveClipIndex] = useState(0);
  const [clipSelectKey, setClipSelectKey] = useState(0);

  const searchParams = useMemo(() => {
    const params = {};
    if (activeSearch?.alertText) {
      params.alert_text = activeSearch.alertText;
    } else if (selectedPerson?.name) {
      params.person_name = selectedPerson.name;
    }

    const region =
      activeSearch?.region ??
      (selectedRegion && selectedRegion !== '전국' ? selectedRegion : null);
    if (region) {
      params.region = region;
    }
    return params;
  }, [
    activeSearch?.alertText,
    activeSearch?.region,
    selectedPerson?.name,
    selectedRegion,
  ]);

  const sidebarPerson = useMemo(
    () => buildSidebarPerson(activeSearch, selectedResult, results[0]),
    [activeSearch, selectedResult, results],
  );

  const loadResults = useCallback(async () => {
    console.log('activeSearch:', activeSearch);
    console.log('searchResultId:', activeSearch?.searchResultId);
    setLoading(true);
    setError(null);
    setSelectedResult(null);
    try {
      if (activeSearch?.searchResultId) {
        const detail = await fetchSearchResultDetail(
          activeSearch.searchResultId,
        );
        console.log('검색 상세 응답:', detail);
        console.log('video_results:', detail.video_results);
        console.log(
          '첫 번째 썸네일 경로:',
          detail.video_results?.[0]?.thumbnail_url,
        );

        console.log(
          '첫 번째 영상 경로:',
          detail.video_results?.[0]?.video_path,
        );
        const videoCards = (detail.video_results || []).map((video) => ({
          ...video,
          id: video.video_id,
          search_id: detail.id,
          person_name: detail.person_name,
          person_age: detail.person_age,
          region: detail.region,
          sms_info: detail.sms_info,
          created_at: detail.created_at,
          description: detail.description,
        }));

        setResults(videoCards);
        return;
      }

      if (!activeSearch && !selectedPerson) {
        setResults([]);
        return;
      }

      const data = await fetchSearchResults(searchParams);
      setResults(data);
    } catch {
      setError('검색 결과를 불러오지 못했습니다.');
      setResults([]);
    } finally {
      setLoading(false);
    }
  }, [activeSearch, selectedPerson, searchParams]);

  useEffect(() => {
    loadResults();
  }, [loadResults]);

  useEffect(() => {
    setActiveClipIndex(0);
  }, [selectedResult?.id]);

  const handleClipSelect = (index) => {
    setActiveClipIndex(index);
    setClipSelectKey((prev) => prev + 1);
  };

  const handleDeleteResult = async (result) => {
    if (
      !window.confirm(
        '이 영상만이 아니라 해당 검색 기록과 모든 분석 결과가 삭제됩니다. 계속할까요?',
      )
    )
      return;

    setDeletingId(result.id);
    setError(null);
    try {
      await deleteSearchResult(result.search_id);
      setResults((prev) =>
        prev.filter((r) => r.search_id !== result.search_id),
      );
      if (selectedResult?.id === result.id) {
        setSelectedResult(null);
      }
    } catch {
      setError('검색 결과를 삭제하지 못했습니다.');
    } finally {
      setDeletingId(null);
    }
  };

  const handleDeleteAll = async () => {
    if (
      !window.confirm(`표시된 검색 결과 ${results.length}건을 모두 삭제할까요?`)
    )
      return;

    setClearingAll(true);
    setError(null);
    try {
      await deleteAllSearchResults(searchParams);
      setResults([]);
      setSelectedResult(null);
    } catch {
      setError('검색 결과를 삭제하지 못했습니다.');
    } finally {
      setClearingAll(false);
    }
  };

  const clipsWithFullUrl = selectedResult?.clips?.map((c) => ({
    ...c,
    url: thumbUrl(c.url),
    thumbnail_url: c.thumbnail_url ? thumbUrl(c.thumbnail_url) : null,
  }));

  const contextLabel = activeSearch
    ? '현재 안내문자'
    : selectedPerson
      ? `${selectedPerson.name} 검색`
      : null;

  const analysisSummary = activeSearch?.analysisSummary;
  const showNoMatchState =
    !loading &&
    !error &&
    !selectedResult &&
    results.length === 0 &&
    analysisSummary?.noMatch;

  const sortedResults = useMemo(() => {
    const list = [...results];
    switch (sortBy) {
      case 'confidence-asc':
        return list.sort((a, b) => a.best_confidence - b.best_confidence);
      case 'newest':
        return list.sort(
          (a, b) => new Date(b.created_at) - new Date(a.created_at),
        );
      case 'oldest':
        return list.sort(
          (a, b) => new Date(a.created_at) - new Date(b.created_at),
        );
      case 'confidence-desc':
      default:
        return list.sort((a, b) => b.best_confidence - a.best_confidence);
    }
  }, [results, sortBy]);
  const confidenceRankMap = useMemo(() => {
    const ranked = [...results].sort(
      (a, b) => (b.best_confidence || 0) - (a.best_confidence || 0),
    );

    return new Map(ranked.map((result, index) => [result.id, index + 1]));
  }, [results]);
  const resultStats = useMemo(() => {
    if (!results.length) return null;
    const maxConfidence = Math.max(
      ...results.map((r) => r.best_confidence || 0),
    );
    const totalClips = results.reduce(
      (sum, r) => sum + (r.clips?.length || 0),
      0,
    );
    return {
      count: results.length,
      maxConfidence: Math.round(maxConfidence * 100),
      totalClips,
    };
  }, [results]);

  return (
    <div className="search-page">
      <header className="search-page__header">
        <h1>검색결과</h1>
        {contextLabel && (
          <span className="search-page__person">
            {contextLabel}
            {(activeSearch?.region || selectedRegion) &&
            (activeSearch?.region || selectedRegion) !== '전국'
              ? ` · ${activeSearch?.region || selectedRegion}`
              : ''}
          </span>
        )}
        {results.length > 0 && !selectedResult && (
          <button
            type="button"
            className="search-page__clear-btn"
            onClick={handleDeleteAll}
            disabled={clearingAll || loading}
          >
            {clearingAll ? '삭제 중…' : '전체 삭제'}
          </button>
        )}
      </header>

      <div className="search-page__panel">
        <main className="search-page__main">
          {!activeSearch && !selectedPerson && (
            <p className="search-page__hint">
              선택한 안내문자 또는 저장된 검색 조건에 맞는 결과가 여기에
              표시됩니다.
            </p>
          )}

          {analysisSummary && (
            <div
              className={`search-page__analysis-banner${
                analysisSummary.noMatch
                  ? ' search-page__analysis-banner--warn'
                  : ''
              }`}
            >
              <div className="search-page__analysis-text">
                {analysisSummary.noMatch ? (
                  <p>
                    분석은 완료되었으나 일치 후보가 없습니다.
                    <span className="search-page__analysis-meta">
                      {analysisSummary.videoFilename}
                    </span>
                  </p>
                ) : (
                  <p>
                    분석 완료 · 탐지 {analysisSummary.totalDetections}건
                    <span className="search-page__analysis-meta">
                      {analysisSummary.videoFilename}
                    </span>
                  </p>
                )}
              </div>
            </div>
          )}

          <div className="search-page__content">
            {loading && <p className="search-page__status">불러오는 중…</p>}
            {error && <p className="search-page__error">{error}</p>}

            {resultStats && !selectedResult && (
              <div className="search-page__stats">
                <span className="search-page__stat">
                  탐지 <strong>{resultStats.count}</strong>건
                </span>
                {resultStats.totalClips > 0 && (
                  <>
                    <span className="search-page__stat">
                      클립 <strong>{resultStats.totalClips}</strong>개
                    </span>
                  </>
                )}
                <div className="search-page__sort">
                  <label htmlFor="result-sort">정렬</label>
                  <select
                    id="result-sort"
                    value={sortBy}
                    onChange={(e) => setSortBy(e.target.value)}
                  >
                    <option value="confidence-desc">신뢰도 높은 순</option>
                    <option value="confidence-asc">신뢰도 낮은 순</option>
                    <option value="newest">최신 순</option>
                    <option value="oldest">오래된 순</option>
                  </select>
                </div>
              </div>
            )}

            {showNoMatchState && (
              <div className="search-page__empty search-page__empty--analysis">
                <p>해당 영상에서 실종자 후보가 탐지되지 않았습니다.</p>
                <p>검색 조건이나 안내문자 내용을 다시 확인해 주세요.</p>
              </div>
            )}

            {!loading &&
              !error &&
              !selectedResult &&
              !showNoMatchState &&
              (results.length === 0 ? (
                <div className="search-page__empty">
                  <p>아직 검색 결과가 없습니다.</p>
                  <p>
                    대시보드에서 안내문자를 선택해 실종자 검색을 진행해 주세요.
                  </p>
                </div>
              ) : (
                <div className="search-grid">
                  {sortedResults.map((r) => (
                    <SearchResultCard
                      key={r.id}
                      result={{
                        ...r,
                        rank: confidenceRankMap.get(r.id),
                        thumbnail_url: thumbUrl(r.thumbnail_url),
                      }}
                      onClick={setSelectedResult}
                      onDelete={handleDeleteResult}
                      deleting={deletingId === r.id || clearingAll}
                    />
                  ))}
                </div>
              ))}

            {selectedResult && clipsWithFullUrl?.length > 0 && (
              <div className="search-page__detail">
                <ClipSequencePlayer
                  clips={clipsWithFullUrl}
                  currentIndex={activeClipIndex}
                  selectCount={clipSelectKey}
                  onClipChange={setActiveClipIndex}
                  onBack={() => setSelectedResult(null)}
                />
                <DetectionCandidateList
                  candidates={clipsWithFullUrl}
                  activeIndex={activeClipIndex}
                  onSelect={handleClipSelect}
                  appearance={
                    sidebarPerson?.clothes ||
                    selectedResult?.sms_info?.clothes ||
                    null
                  }
                />
              </div>
            )}

            {selectedResult && !clipsWithFullUrl?.length && (
              <div className="search-page__empty">
                <p>
                  <strong>{selectedResult.person_name}</strong> 검색 기록입니다.
                </p>
                <p>
                  {selectedResult.description ||
                    '영상 클립 결과는 분석 상세 API 연동 후 표시됩니다.'}
                </p>
                <button
                  type="button"
                  className="search-page__clear-btn"
                  onClick={() => setSelectedResult(null)}
                >
                  목록으로
                </button>
              </div>
            )}
          </div>
        </main>
      </div>
    </div>
  );
}
