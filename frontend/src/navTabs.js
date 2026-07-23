/** DashboardLayout·LandingHeader가 공유하는 상단 탭 목록.
 *
 * 예전에 두 헤더에 각자 복사해서 썼더니, 한쪽만 수정되고 다른 쪽은
 * 안 바뀌는 불일치가 생겼다(실종자 관리 탭이 LandingHeader엔 없었음) —
 * 그래서 여기 하나로 모아두고 양쪽에서 그대로 가져다 쓴다.
 */
export const NAV_TABS = [
  { to: '/dashboard', label: '실종자 검색', end: true },
  { to: '/dashboard/chatbot', label: '챗봇 검색' },
  { to: '/search-results', label: '검색 결과' },
  { to: '/dashboard/history', label: '검색 이력' },
  { to: '/dashboard/cases', label: '실종자 관리', roles: ['1', '2'] }, // 1:관리자, 2:수사관만
];

/** role(로그인 안 했으면 null)에 따라 실제로 보여줄 탭만 걸러낸다. */
export function getVisibleNavTabs(role) {
  return NAV_TABS.filter((tab) => !tab.roles || tab.roles.includes(role));
}
