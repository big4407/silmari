/** /dev 테스트 허브 사이드바 메뉴 */
export const DEV_PAGES = [
  { path: "", label: "개요", desc: "API 테스트 허브 홈" },
  { path: "health", label: "헬스체크", desc: "GET /health, GET /" },
  { path: "auth", label: "인증", desc: "로그인·토큰·회원·RBAC" },
  { path: "messages", label: "재난문자", desc: "수집·조회·수동등록" },
  { path: "alert", label: "안내문자 파싱", desc: "POST /api/alert/parse" },
  { path: "search", label: "검색 요청", desc: "POST/GET/DELETE /search" },
  { path: "disaster", label: "재난 알림", desc: "GET /api/alerts/list" },
  { path: "result", label: "탐지 결과", desc: "GET /api/result/*" },
  { path: "cctv", label: "CCTV 분석", desc: "POST /api/cctv/analyze" },
  { path: "chatbot", label: "챗봇", desc: "POST /chatbot/chat" },
  { path: "admin", label: "관리자", desc: "회원 승인·목록" },
]

export function devPageTitle(subPath) {
  const page = DEV_PAGES.find((p) => p.path === subPath)
  return page?.label ?? "Dev"
}
