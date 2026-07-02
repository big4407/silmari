/**
 * 개발용 API 클라이언트 — /dev 테스트 페이지 전용.
 * sessionStorage에 토큰을 저장하고 Authorization 헤더를 자동 첨부한다.
 */
import axios from "axios"

/** 백엔드 주소 (로컬 FastAPI) */
export const API_BASE = "http://127.0.0.1:8000"
/** sessionStorage 키 — 로그인 후 access/refresh 토큰 JSON 저장 */
const TOKEN_KEY = "silmari_dev_tokens"

// --- 토큰 저장소 (sessionStorage) ---

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

// --- axios 인스턴스 + 요청 인터셉터 (Bearer 토큰 자동 첨부) ---

const devClient = axios.create({ baseURL: API_BASE })

devClient.interceptors.request.use((config) => {
  const tokens = getStoredTokens()
  if (tokens?.access_token) {
    config.headers.Authorization = `Bearer ${tokens.access_token}`
  }
  return config
})

export default devClient
