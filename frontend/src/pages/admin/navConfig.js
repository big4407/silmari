/** 관리자 콘솔 사이드바 메뉴 구조와 viewId 매핑 */
export const NAV = [
  { id: 'dashboard', label: '대시보드', solo: true },
  {
    group: '회원 관리',
    items: [
      { id: 'members-pending', label: '가입 승인 대기' },
      { id: 'members-all', label: '전체 회원' },
    ],
  },
  {
    group: '실종 안내문자',
    items: [{ id: 'reports', label: '안내문자 목록' }],
  },
  {
    group: '실종자 관리',
    items: [{ id: 'case-assignment', label: '실종사건 관리' }],
  },
  {
    group: 'CCTV·검색 운영',
    items: [
      { id: 'cctv-source', label: 'CCTV 영상 수집 현황' },
      { id: 'search-requests', label: '검색 요청 이력' },
    ],
  },
  {
    group: 'LLM 운영 관리',
    items: [{ id: 'llm-usage', label: 'LLM 사용량' }],
  },
  {
    group: '통계',
    items: [
      { id: 'stats-cctv', label: 'CCTV 영상 통계' },
      { id: 'stats-search', label: '검색 통계' },
      { id: 'stats-demographic', label: '성별·연령·지역별 실종/검색율' },
      { id: 'stats-outcomes', label: '발견/해결 결과 통계' },
      { id: 'stats-export', label: '통계데이터 내보내기' },
    ],
  },
  {
    group: '데이터 관리',
    items: [
      { id: 'data-codes', label: '행정구역 관리' },
      { id: 'data-validate', label: '데이터 정합성 점검' },
      { id: 'data-retention', label: '삭제·보존 정책' },
    ],
  },
  {
    group: '감사 로그',
    items: [
      { id: 'audit-admin', label: '관리자 활동 이력' },
      { id: 'audit-approval', label: '승인·권한변경 이력' },
      { id: 'audit-login', label: '로그인·접근 이력' },
    ],
  },
];

export const crumbOf = {};
NAV.forEach((node) => {
  if (node.solo) {
    crumbOf[node.id] = ['대시보드'];
    return;
  }
  node.items.forEach((item) => {
    crumbOf[item.id] = [node.group, item.label];
  });
});

export const DEFAULT_VIEW = 'dashboard';

export function isValidViewId(id) {
  return Boolean(crumbOf[id]);
}
