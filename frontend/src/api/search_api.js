/**
 * 검색 요청 API — /api/search-requests/*
 * 실종자 검색 건 등록·조회. DevSearchPage에서 테스트.
 */
import devClient from "./devClient"
import { API_V1 } from "./client"

const BASE = `${API_V1}/search-requests`

/** 새 검색 요청 생성 (user_id, 실종자 정보 등) */
export const createSearch = async (payload) => {
  const { data } = await devClient.post(BASE, payload)
  return data
}

/** 검색 요청 목록 */
export const fetchSearches = async (params = {}) => {
  const { data } = await devClient.get(BASE, { params })
  return data
}

/** 검색 요청 단건 상세 */
export const fetchSearch = async (searchId) => {
  const { data } = await devClient.get(`${BASE}/${searchId}`)
  return data
}

/** 검색 요청 삭제 */
export const deleteSearch = async (searchId) => {
  await devClient.delete(`${BASE}/${searchId}`)
}
