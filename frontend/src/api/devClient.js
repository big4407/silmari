/**
 * 개발용 API 클라이언트 — /dev 테스트 페이지 전용.
 * sessionStorage에 토큰을 저장하고 Authorization 헤더를 자동 첨부한다.
 */
import axios from "axios"

export const API_BASE = "http://localhost:8000"
const TOKEN_KEY = "silmari_dev_tokens"

export function getStoredTokens() {
  try {
    const raw = sessionStorage.getItem(TOKEN_KEY)
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

export function setStoredTokens(tokens) {
  sessionStorage.setItem(TOKEN_KEY, JSON.stringify(tokens))
}

export function clearStoredTokens() {
  sessionStorage.removeItem(TOKEN_KEY)
}

const devClient = axios.create({ baseURL: API_BASE })

devClient.interceptors.request.use((config) => {
  const tokens = getStoredTokens()
  if (tokens?.access_token) {
    config.headers.Authorization = `Bearer ${tokens.access_token}`
  }
  return config
})

export default devClient
