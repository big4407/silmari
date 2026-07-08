/**
 * 대시보드 전역 상태 — Zustand 스토어.
 *
 * [연동] Dashboard(재난문자·지역) ↔ SearchResults(결과) ↔ SearchHistory(이력)
 * [핵심] alertText, selectedRegion, activeSearch — 화면 간 탐지 컨텍스트 공유
 */
import { create } from 'zustand';

export const useDetectionStore = create((set) => ({
  alertText: '',
  selectedPerson: null,
  selectedAlert: null,
  alertList: [],
  activeSearch: null,
  selectedRegion: '전국',
  startDate: '',
  endDate: '',
  contentKeyword: '',
  missingList: [],
  loading: false,

  setAlertText: (text) => set({ alertText: text }),
  setSelectedPerson: (person) =>
    set({ selectedPerson: person, activeSearch: null }),
  setSelectedAlert: (alert) => set({ selectedAlert: alert }),
  setAlertList: (list) => set({ alertList: list }),
  setActiveSearch: (search) =>
    set({ activeSearch: search, selectedPerson: null }),
  clearActiveSearch: () => set({ activeSearch: null }),
  setSelectedRegion: (region) => set({ selectedRegion: region }),
  setStartDate: (date) => set({ startDate: date }),
  setEndDate: (date) => set({ endDate: date }),
  setContentKeyword: (keyword) => set({ contentKeyword: keyword }),
  setMissingList: (list) => set({ missingList: list }),
  setLoading: (loading) => set({ loading }),
}));
