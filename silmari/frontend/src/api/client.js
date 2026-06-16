import axios from "axios"

export const API_BASE = "http://localhost:8000"

const client = axios.create({
  baseURL: API_BASE,
})

export const analyzeVideo = (formData) =>
  client.post("/api/cctv/analyze", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  }).then(r => r.data)

export const fetchMissingList = (params = {}) =>
  client.get("/api/result/list", { params }).then(r => r.data)

export const fetchSearchResults = (params = {}) =>
  client.get("/api/result/search", { params }).then(r => r.data)

export const fetchSearchResultDetail = (id) =>
  client.get(`/api/result/search/${id}`).then(r => r.data)

export const deleteSearchResult = (id) =>
  client.delete(`/api/result/search/${id}`).then(r => r.data)

export const deleteAllSearchResults = (params = {}) =>
  client.delete("/api/result/search", { params }).then(r => r.data)

export const fetchDisasterAlerts = (params = {}) =>
  client.get("/api/alerts/list", { params }).then(r => r.data)

export default client
