/**
 * 재난문자 API — /api/messages/*
 * DevMessagesPage에서 CRUD·수집 테스트에 사용. devClient(인증 헤더) 경유.
 */
import devClient from "./devClient"
import { API_V1 } from "./client"

const BASE = `${API_V1}/messages`

/** 외부(행안부) API에서 재난문자를 가져와 DB에 저장 */
export const collectMessages = async (params = {}) => {
  const { data } = await devClient.post(`${BASE}/collect`, null, { params })
  return data
}

/** 저장된 재난문자 목록 (페이지네이션) */
export const fetchMessages = async (params = {}) => {
  const { data } = await devClient.get(BASE, { params })
  return data
}

/** 일련번호(sn)로 재난문자 단건 조회 */
export const fetchMessage = async (sn) => {
  const { data } = await devClient.get(`${BASE}/${sn}`)
  return data
}

/** 테스트용 재난문자 수동 등록 */
export const createMessage = async (payload) => {
  const { data } = await devClient.post(`${BASE}/manual_input`, payload)
  return data
}

/** 재난문자 삭제 */
export const deleteMessage = async (sn) => {
  await devClient.delete(`${BASE}/${sn}`)
}
