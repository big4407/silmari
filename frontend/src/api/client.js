/**
 * 백엔드 API 클라이언트 — axios 래퍼.
 *
 * [베이스] localhost:8000 (개발) — 배포 시 환경변수로 교체 필요
 * [인증]  signup, login, logout → /member/auth/* (JWT + localStorage)
 * [탐지]  analyzeVideo → POST /api/video/analyze
 * [결과]  fetchSearchResults, fetchSearchResultDetail → /api/missing/search
 * [재난]  fetchDisasterAlerts → /api/alerts/list (Dashboard)
 */
import axios from 'axios';

export const API_BASE = 'http://localhost:8000';

// ── 토큰 저장소 (localStorage) ─────────────────────────────
const ACCESS_KEY = 'silmari_access_token';
const REFRESH_KEY = 'silmari_refresh_token';

export const tokenStore = {
  getAccess: () => localStorage.getItem(ACCESS_KEY),
  getRefresh: () => localStorage.getItem(REFRESH_KEY),
  set: (access, refresh) => {
    if (access) localStorage.setItem(ACCESS_KEY, access);
    if (refresh) localStorage.setItem(REFRESH_KEY, refresh);
  },
  clear: () => {
    localStorage.removeItem(ACCESS_KEY);
    localStorage.removeItem(REFRESH_KEY);
  },
};

const client = axios.create({
  baseURL: API_BASE,
});

// ── 요청 인터셉터: access 토큰을 Authorization 헤더에 자동 첨부 ──
client.interceptors.request.use((config) => {
  const token = tokenStore.getAccess();
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// ══════════════════════════════════════════════════════════
// 인증 (auth) — /member/auth/*
// ══════════════════════════════════════════════════════════

/**
 * 회원가입 신청 (승인 대기 상태로 생성).
 * @param {{username, email, password, full_name, organization, phone,
 *          department?, position?, requested_role?}} payload
 * @returns {Promise<{message, user}>}
 */
export const signup = (payload) =>
  client.post('/member/auth/signup', payload).then((r) => r.data);

/**
 * 로그인. 성공 시 토큰을 localStorage에 저장한다.
 * @param {string} username
 * @param {string} password
 * @returns {Promise<{access_token, refresh_token, token_type, access_expires_in_seconds}>}
 */
export const login = async (username, password) => {
  const { data } = await client.post('/member/auth/login', {
    username,
    password,
  });
  tokenStore.set(data.access_token, data.refresh_token);
  return data;
};

/**
 * 로그아웃. 서버 세션을 무효화하고 로컬 토큰을 지운다.
 * 서버 호출이 실패해도 로컬 토큰은 항상 제거한다.
 */
export const logout = async () => {
  try {
    await client.post('/member/auth/logout');
  } finally {
    tokenStore.clear();
  }
};

/** 로그인 여부 (access 토큰 보유 여부) */
export const isAuthenticated = () => Boolean(tokenStore.getAccess());

/**
 * access 토큰(JWT)의 payload를 디코드한다. 서명 검증은 하지 않으며,
 * 화면 표시·분기용으로만 사용한다(실제 권한 검증은 서버가 함).
 * @returns {object|null}
 */
const decodeAccessToken = () => {
  const token = tokenStore.getAccess();
  if (!token) return null;
  try {
    const payload = token.split('.')[1];
    // base64url → base64 → JSON
    const json = atob(payload.replace(/-/g, '+').replace(/_/g, '/'));
    return JSON.parse(json);
  } catch {
    return null;
  }
};

/** 현재 로그인 사용자의 역할 코드('1'관리자/'2'수사관/'3'공무원) 또는 null */
export const getRole = () => decodeAccessToken()?.role ?? null;

/** 현재 사용자가 관리자('1')인지 */
export const isAdmin = () => getRole() === '1';

// ══════════════════════════════════════════════════════════
// 관리자 (admin) — /member/admin/*
// ══════════════════════════════════════════════════════════

// 역할/상태 코드 ↔ 한글 라벨 (DB엔 숫자 코드로 저장됨)
export const ROLE_LABELS = { 1: '관리자', 2: '수사관', 3: '공무원' };
export const STATUS_LABELS = { 0: '대기', 1: '승인', 2: '반려', 3: '정지' };
export const roleLabel = (code) => ROLE_LABELS[code] ?? '-';
export const statusLabel = (code) => STATUS_LABELS[code] ?? '-';

/**
 * 회원 목록 조회. approvalStatus 지정 시 해당 상태만 필터.
 * @param {string} [approvalStatus] '0'(대기)/'1'(승인)/'2'(반려)/'3'(정지)
 * @returns {Promise<Array>} UserResponse[]
 */
export const fetchUsers = (approvalStatus) => {
  const params =
    approvalStatus != null ? { approval_status: approvalStatus } : {};
  return client.get('/member/admin/users', { params }).then((r) => r.data);
};

/**
 * 승인 상태 변경(승인/반려/정지).
 * @param {string} userId
 * @param {{status: string, role?: string, rejection_reason?: string}} payload
 *        status: '1'승인 / '2'반려 / '3'정지, role: 승인 시 부여할 역할 코드
 * @returns {Promise<Object>} 갱신된 UserResponse
 */
export const updateApproval = (userId, payload) =>
  client
    .patch(`/member/admin/users/${userId}/approval`, payload)
    .then((r) => r.data);

// ===============================
// 안내문자 관련
// ===============================
export const getMessageList = ({
  page,
  per_page,
  content,
  region,
  startDate,
  endDate,
  orderBy,
}) => {
  return client
    .get('/message', {
      params: {
        page: page,
        per_page: per_page,
        search_content: content || null,
        region: region || null,
        start_date: startDate,
        end_date: endDate,
        order_by: orderBy,
      },
    })
    .then((r) => r.data);
};

// ══════════════════════════════════════════════════════════
// 레거시 (초기 단발 파이프라인) — /api/video, /api/missing, /api/alerts
// ══════════════════════════════════════════════════════════

export const analyzeVideo = (formData) =>
  client
    .post('/api/video/analyze', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    .then((r) => r.data);

export const fetchMissingList = (params = {}) =>
  client.get('/api/missing/list', { params }).then((r) => r.data);

export const fetchSearchResults = (params = {}) =>
  client.get('/api/missing/search', { params }).then((r) => r.data);

export const fetchSearchResultDetail = (id) =>
  client.get(`/api/missing/search/${id}`).then((r) => r.data);

export const deleteSearchResult = (id) =>
  client.delete(`/api/missing/search/${id}`).then((r) => r.data);

export const deleteAllSearchResults = (params = {}) =>
  client.delete('/api/missing/search', { params }).then((r) => r.data);

export const fetchDisasterAlerts = (params = {}) =>
  client.get('/api/alerts/list', { params }).then((r) => r.data);

export default client;
