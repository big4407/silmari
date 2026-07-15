/**
 * 백엔드 API 클라이언트 — axios 래퍼.
 *
 * [베이스] localhost:8000 (개발) — 배포 시 환경변수로 교체 필요
 * [인증]  signup, login, logout → /member/auth/*
 * [재난]  fetchMessages, collectMessages → /message/*
 * [검색]  fetchSearchList, fetchSearchDetail → /search/*
 * [챗봇]  chatbot_api.js → /chatbot/*
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

// ── 응답 인터셉터: access 토큰 만료(401) 시 refresh 로 자동 재발급 후 원요청 재시도 ──
// 동시에 여러 요청이 401 나도 refresh 는 한 번만 수행하고, 나머지는 그 결과를 기다린다.
let _refreshing = null;
let _loggingOut = false;

const isAuthBypassCall = (url = '') =>
  url.includes('/member/auth/refresh') || url.includes('/member/auth/logout');

const doRefresh = async () => {
  if (_loggingOut) throw new Error('logging out');
  const refreshToken = tokenStore.getRefresh();
  if (!refreshToken) throw new Error('no refresh token');
  // 인터셉터 무한루프 방지를 위해 raw axios 로 호출(client 대신)
  const { data } = await axios.post(`${API_BASE}/member/auth/refresh`, {
    refresh_token: refreshToken,
  });
  if (_loggingOut) throw new Error('logging out');
  tokenStore.set(data.access_token, data.refresh_token);
  return data.access_token;
};

client.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config;
    const status = error.response?.status;

    // 401 이고, 아직 재시도 안 했고, refresh/logout 요청이 아닌 경우에만
    if (
      status === 401 &&
      !original?._retry &&
      !isAuthBypassCall(original?.url) &&
      !_loggingOut
    ) {
      original._retry = true;
      try {
        // 이미 갱신 중이면 그 Promise 를 공유(중복 refresh 방지)
        if (!_refreshing)
          _refreshing = doRefresh().finally(() => (_refreshing = null));
        const newAccess = await _refreshing;
        original.headers.Authorization = `Bearer ${newAccess}`;
        return client(original); // 새 토큰으로 원요청 재시도
      } catch (e) {
        // refresh 도 실패(만료/무효) → 토큰 정리 후 로그인 유도
        tokenStore.clear();
        if (typeof window !== 'undefined' && !_loggingOut) {
          window.location.assign('/login');
        }
        return Promise.reject(e);
      }
    }
    return Promise.reject(error);
  },
);

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
 * 로그아웃. 로컬 토큰을 먼저 지운 뒤 서버 세션을 무효화한다.
 * 서버가 응답하지 않아도 로컬 세션은 즉시 종료된다.
 */
export const logout = async () => {
  if (_loggingOut) return;
  _loggingOut = true;
  _refreshing = null;

  const accessToken = tokenStore.getAccess();
  tokenStore.clear();

  try {
    if (accessToken) {
      await axios.post(
        `${API_BASE}/member/auth/logout`,
        {},
        {
          headers: { Authorization: `Bearer ${accessToken}` },
          timeout: 5000,
        },
      );
    }
  } catch {
    // 서버 무응답·세션 만료 등 — 로컬 토큰은 이미 제거됨
  } finally {
    _loggingOut = false;
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

/** 현재 로그인 사용자 ID (JWT sub) 또는 null */
export const getUserId = () => decodeAccessToken()?.sub ?? null;

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
// 감사 로그 — 로그인 이력 (/member/admin/login-history)
// ══════════════════════════════════════════════════════════

/** 로그인 이력(감사 로그) 조회. */
export const fetchLoginHistory = (params = {}) =>
  client.get('/member/admin/login-history', { params }).then((r) => r.data);

/** 관리자 행동 이력(감사 로그) 조회. approval_only=true 면 승인·권한 변경만. */
export const fetchAdminHistory = (params = {}) =>
  client.get('/member/admin/admin-history', { params }).then((r) => r.data);

/** 검색 요청 이력(관리자용, 전체 사용자 대상) */
export const fetchAdminSearchRequests = (params = {}) =>
  client.get('/member/admin/search-requests', { params }).then((r) => r.data);

/** CCTV 영상 수집 현황(관리자용, 지역별 집계) */
export const fetchCctvCoverage = () =>
  client.get('/member/admin/cctv-coverage').then((r) => r.data);

/** 행정구역 목록 */
export const fetchRegions = (params = {}) =>
  client.get('/member/admin/regions', { params }).then((r) => r.data);

/** 행정구역 상세 */
export const fetchRegionDetail = (regionCode) =>
  client.get(`/member/admin/regions/${regionCode}`).then((r) => r.data);

/** 상위 지역 선택용 옵션 목록 */
export const fetchRegionOptions = () =>
  client.get('/member/admin/regions/options').then((r) => r.data);

/** 행정구역 등록 */
export const createRegion = (payload) =>
  client.post('/member/admin/regions', payload).then((r) => r.data);

/** 행정구역 수정 */
export const updateRegion = (regionCode, payload) =>
  client
    .patch(`/member/admin/regions/${regionCode}`, payload)
    .then((r) => r.data);

/** 행정구역 삭제 */
export const deleteRegion = (regionCode) =>
  client.delete(`/member/admin/regions/${regionCode}`);

/** 행정구역·법정동 매핑 전체 삭제 */
export const clearAllRegions = () =>
  client.post('/member/admin/regions/clear-all').then((r) => r.data);

/** 행정구역 CSV보내기 */
export const exportRegionsCsv = (format = 'region') =>
  client
    .get('/member/admin/regions/export.csv', {
      params: { format },
      responseType: 'blob',
    })
    .then((r) => r.data);

/** 행정구역 CSV 가져오기 (dryRun=true면 검증만) */
export const importRegionsCsv = (file, dryRun = false) => {
  const formData = new FormData();
  formData.append('file', file);
  return client
    .post('/member/admin/regions/import.csv', formData, {
      params: { dry_run: dryRun },
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    .then((r) => r.data);
};

/** 보존 정책 목록. */
export const fetchRetentionPolicies = () =>
  client.get('/member/admin/retention-policies').then((r) => r.data);

/** 보존 정책 일괄 수정. */
export const updateRetentionPolicies = (policies) =>
  client
    .patch('/member/admin/retention-policies', { policies })
    .then((r) => r.data);

/** 보존 정책 드라이런 — 만료 대상 건수·샘플 미리보기. */
export const runRetentionDryRun = ({ policyId = null, policies = null } = {}) =>
  client
    .post(
      '/member/admin/retention-policies/dry-run',
      policies?.length ? { policies } : {},
      { params: policyId ? { policy_id: policyId } : {} },
    )
    .then((r) => r.data);

/** 정합성 검사 실행. */
export const runDataIntegrity = () =>
  client.post('/member/admin/data-integrity/run').then((r) => r.data);

/** 최근 정합성 검사 결과 (감사 로그). 없으면 404. */
export const fetchLastIntegrityRun = () =>
  client.get('/member/admin/data-integrity/last').then((r) => r.data);

/** 감사 로그 ID로 정합성 검사 결과 복원. */
export const fetchIntegrityRun = (runId) =>
  client.get(`/member/admin/data-integrity/runs/${runId}`).then((r) => r.data);

/** 검사 항목별 전체 이슈 목록. */
export const fetchIntegrityCheckIssues = (checkId) =>
  client
    .get(`/member/admin/data-integrity/checks/${checkId}/issues`)
    .then((r) => r.data);

/** 정합성 검사 CSV 리포트보내기. source: last | fresh */
export const downloadIntegrityReport = (source = 'last') =>
  client
    .get('/member/admin/data-integrity/report.csv', {
      params: { source },
      responseType: 'blob',
    })
    .then((r) => r.data);

/** Blob 파일 다운로드 */
export const saveBlobDownload = (blob, filename) => {
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
};

/** API 오류 메시지 추출 (blob 응답 포함) */
export const readApiErrorMessage = async (err, fallback) => {
  const detail = err?.response?.data?.detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    return detail.map((item) => item.msg || JSON.stringify(item)).join(', ');
  }

  const data = err?.response?.data;
  if (data instanceof Blob) {
    try {
      const text = await data.text();
      const parsed = JSON.parse(text);
      if (typeof parsed.detail === 'string') return parsed.detail;
    } catch {
      // fall through to fallback
    }
  }

  return fallback;
};

// 관리자 행동 유형 코드 → 한글 라벨 (AdminAction enum)
//   "1" 승인 / "2" 반려 / "3" 정지 / "4" 재승인 / "5" 삭제 / "6" 수정
export const ADMIN_ACTION_LABELS = {
  1: '승인',
  2: '반려',
  3: '정지',
  4: '재승인',
  5: '삭제',
  6: '수정',
};

// 검색 요청 출처 코드 → 한글 라벨 (SearchType enum)
export const SEARCH_TYPE_LABELS = {
  1: '안내문자',
  2: '챗봇',
  3: '자동검색',
};

// 로그인 실패 사유 — 화면 표시용 라벨.
// DB/응답에는 숫자 코드("1"~"5")로 저장·전달되고(LoginFailReason enum),
// 사용자에게는 아래 한글로 변환해 보여준다. (성공 시 fail_reason 은 없음)
//   "1" 아이디 없음 또는 비밀번호 불일치
//   "2" 승인 대기 중인 계정
//   "3" 가입 반려된 계정
//   "4" 정지된 계정
//   "5" 역할 미부여 계정
export const LOGIN_FAIL_LABELS = {
  1: '비밀번호 불일치',
  2: '승인 대기',
  3: '반려된 계정',
  4: '정지된 계정',
  5: '역할 미부여',
};

// ══════════════════════════════════════════════════════════
// 재난문자 — /message/*
// ══════════════════════════════════════════════════════════

/** DB에 저장된 재난문자 목록 조회 */
export const fetchMessages = (params = {}) =>
  client.get('/message', { params }).then((r) => r.data);

/** 안내문자 본문에서 LLM으로 실종자 정보(이름·성별·나이·인상착의) 추출 */
export const parseAlertMessage = (msgCn) =>
  client.post('/message/parse', { msg_cn: msgCn }).then((r) => r.data);

/** 외부 API에서 재난문자 수집 후 DB 저장 */
export const collectMessages = (params = {}) =>
  client.post('/message/collect', null, { params }).then((r) => r.data);

// ══════════════════════════════════════════════════════════
// 검색 요청 — /search/*
// ══════════════════════════════════════════════════════════

export const fetchSearchList = (params = {}) =>
  client.get('/search', { params }).then((r) => r.data);

/** 검색 요청 생성 + 분석 실행 — POST /search */
export const createSearch = (payload) =>
  client.post('/search', payload).then((r) => r.data);

export const fetchSearchDetail = (id) =>
  client.get(`/search/${id}`).then((r) => r.data);

export const deleteSearch = (id) => client.delete(`/search/${id}`);

function mapSearchItemToHistory(item) {
  return {
    id: item.id,
    person_name: item.missing_name || '미상',
    person_age: item.age,
    region: item.missing_location || '-',
    alert_text: null,
    video_filename: null,
    description: item.clothing,
    created_at: item.searched_at,
    best_confidence: null,
    sms_info: { gender: item.gender, clothes: item.clothing },
  };
}

function mapSearchItemToResult(item) {
  const results = item.analysis_results || [];
  const groupedByVideo = results.reduce((groups, result) => {
    const videoId = result.video_id;

    if (!groups[videoId]) {
      groups[videoId] = [];
    }

    groups[videoId].push(result);
    return groups;
  }, {});
  const bestResult =
    results.length > 0
      ? results.reduce((best, current) =>
          current.matching_rate > best.matching_rate ? current : best,
        )
      : null;

  return {
    id: item.id,
    person_name: item.missing_name || '미상',
    person_age: item.age,
    region: item.missing_location || '-',

    video_results: Object.entries(groupedByVideo).map(
      ([videoId, videoResults]) => {
        const bestVideoResult = videoResults.reduce((best, current) =>
          current.matching_rate > best.matching_rate ? current : best,
        );

        return {
          video_id: Number(videoId),
          video_path: bestVideoResult.video_path || '',
          recorded_at: bestVideoResult.recorded_at,
          thumbnail_url: bestVideoResult.crop_img_path || '',
          best_confidence: bestVideoResult.matching_rate || 0,
          best_timestamp_sec: bestVideoResult.video_timestamp,
          clips: videoResults.map((result) => ({
            id: result.id,
            video_id: result.video_id,
            url: result.video_path || '',
            start_sec: result.video_timestamp,
            end_sec: result.video_timestamp + 5,
            thumbnail_url: result.crop_img_path || '',
            confidence: result.matching_rate,
            position: result.position,
          })),
        };
      },
    ),

    thumbnail_url: bestResult?.crop_img_path || '',
    best_confidence: bestResult?.matching_rate || 0,
    best_timestamp_sec: bestResult?.video_timestamp ?? null,
    clips: results.map((result) => ({
      id: result.id,
      video_id: result.video_id,
      url: result.video_path || '',
      start_sec: result.video_timestamp,
      end_sec: result.video_timestamp + 5,
      thumbnail_url: result.crop_img_path || '',
      confidence: result.matching_rate,
      position: result.position,
    })),

    sms_info: {
      gender: item.gender,
      clothes: item.clothing,
    },
    created_at: item.searched_at,
    description: item.clothing || '',
  };
}

/** 검색 이력 화면용 — GET /search */
export const fetchSearchHistory = async (params = {}) => {
  const size = params.limit || 100;
  const data = await fetchSearchList({ page: 1, size });
  return (data.items || []).map(mapSearchItemToHistory);
};

/** 검색 결과 목록 — GET /search (필터는 클라이언트에서 적용) */
export const fetchSearchResults = async (params = {}) => {
  const data = await fetchSearchList({ page: 1, size: 100 });
  let items = (data.items || []).map(mapSearchItemToResult);
  if (params.person_name) {
    const q = params.person_name.toLowerCase();
    items = items.filter((i) => i.person_name?.toLowerCase().includes(q));
  }
  if (params.region) {
    const q = params.region.toLowerCase();
    items = items.filter((i) => i.region?.toLowerCase().includes(q));
  }
  return items;
};

export const fetchSearchResultDetail = async (id) => {
  const item = await fetchSearchDetail(id);
  return mapSearchItemToResult(item);
};

export const deleteSearchResult = (id) =>
  deleteSearch(id).then((r) => r?.data ?? { ok: true });

export const deleteAllSearchResults = async () => {
  const data = await fetchSearchList({ page: 1, size: 100 });
  const items = data.items || [];
  await Promise.all(items.map((item) => deleteSearch(item.id)));
  return { ok: true, deleted_count: items.length };
};

export default client;
