import { create } from "zustand"

export const useDetectionStore = create((set) => ({
  alertText: "",
  selectedPerson: null,
  selectedAlert: null,
  alertList: [],
  activeSearch: null,
  selectedRegion: "전국",
  startDate: "",
  endDate: "",
  contentKeyword: "",
  missingList: [],
  loading: false,

  setAlertText: (text) => set({ alertText: text }),
  setSelectedPerson: (person) => set({ selectedPerson: person, activeSearch: null }),
  setSelectedAlert: (alert) => set({ selectedAlert: alert }),
  setAlertList: (list) => set({ alertList: list }),
  setActiveSearch: (search) => set({ activeSearch: search, selectedPerson: null }),
  clearActiveSearch: () => set({ activeSearch: null }),
  setSelectedRegion: (region) => set({ selectedRegion: region }),
  setStartDate: (date) => set({ startDate: date }),
  setEndDate: (date) => set({ endDate: date }),
  setContentKeyword: (keyword) => set({ contentKeyword: keyword }),
  setMissingList: (list) => set({ missingList: list }),
  setLoading: (loading) => set({ loading }),
}))
