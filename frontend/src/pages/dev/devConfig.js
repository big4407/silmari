/** /dev 테스트 허브 사이드바 — 관리자 콘솔 navConfig 와 동일한 그룹 구조 */
export const DEV_NAV = [
  { solo: true, path: '', label: '개요', desc: 'API 테스트 허브 홈' },
  {
    group: '시스템',
    items: [
      { path: 'health', label: '헬스체크', desc: 'GET /health, GET /' },
      { path: 'auth', label: '인증', desc: '로그인·토큰·회원·RBAC' },
    ],
  },
  {
    group: '메시지 · 알림',
    items: [
      { path: 'messages', label: '재난문자', desc: 'GET /api/v1/messages' },
      { path: 'alert', label: '안내문자 파싱', desc: 'POST /api/v1/alerts/parse' },
      { path: 'disaster', label: '재난 알림', desc: 'GET /api/v1/disaster-alerts' },
    ],
  },
  {
    group: '검색 · 탐지',
    items: [
      { path: 'search', label: '검색 요청', desc: 'GET/POST /api/v1/search-requests' },
      { path: 'result', label: '탐지 결과', desc: 'GET /api/v1/detection-results' },
      { path: 'cctv', label: 'CCTV 분석', desc: 'POST /api/v1/cctv/analyze' },
    ],
  },
  {
    group: '기타',
    items: [
      { path: 'chatbot', label: '챗봇', desc: 'POST /api/v1/chatbot/chat' },
      { path: 'admin', label: '관리자', desc: '회원 승인·목록' },
    ],
  },
];

/** 허브 카드 그리드용 — solo + 그룹 items 평탄화 */
export const DEV_PAGES = DEV_NAV.flatMap((node) =>
  node.solo
    ? [{ path: node.path, label: node.label, desc: node.desc }]
    : node.items.map((item) => ({
        path: item.path,
        label: item.label,
        desc: item.desc,
      })),
);

/** 현재 서브 경로에 맞는 페이지 제목 */
export function devPageTitle(subPath) {
  const page = DEV_PAGES.find((p) => p.path === subPath);
  return page?.label ?? 'Dev';
}
