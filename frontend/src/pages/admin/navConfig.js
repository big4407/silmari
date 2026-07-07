/** 관리자 콘솔 사이드바 메뉴 구조 — viewId → AdminViewPage 뷰 매핑 */
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
    items: [
      { id: 'reports', label: '안내문자 목록' },
      { id: 'parse-review', label: '인상착의 파싱 검수' },
    ],
  },
  {
    group: 'CCTV·검색 운영',
    items: [
      { id: 'cctv-source', label: 'CCTV 영상 수집' },
      { id: 'search-requests', label: '검색 요청 이력' },
      { id: 'search-jobs', label: '검색 작업 현황' },
      { id: 'match-review', label: '후보 매칭 결과 검토' },
    ],
  },
  {
    group: 'LLM 운영 관리',
    items: [
      { id: 'llm-usage', label: '모델별 사용량' },
      { id: 'llm-cost', label: '토큰·비용' },
      { id: 'llm-perf', label: '응답시간·오류율' },
      { id: 'llm-logs', label: '프롬프트·결과 로그' },
    ],
  },
  {
    group: '분석 리포트',
    items: [
      { id: 'rep-time', label: '실종 발생 시점 분석' },
      { id: 'rep-region', label: '지역·장소 분석' },
      { id: 'rep-search', label: '검색 성능 분석' },
    ],
  },
  {
    group: '데이터 관리',
    items: [
      { id: 'data-codes', label: '기준 코드 관리' },
      { id: 'data-validate', label: '데이터 정합성 검사' },
      { id: 'data-retention', label: '삭제·보존 정책' },
    ],
  },
  {
    group: '감사 로그',
    items: [
      { id: 'audit-admin', label: '관리자 행동 이력' },
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
  node.items.forEach((it) => {
    crumbOf[it.id] = [node.group, it.label];
  });
});

export const DEFAULT_VIEW = 'dashboard';

export function isValidViewId(id) {
  return Boolean(crumbOf[id]);
}
