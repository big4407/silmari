/** /dev 테스트 허브 사이드바 메뉴 — path는 /dev/{path} 라우트와 1:1 대응 */
export const DEV_PAGES = [
  { path: "", label: "개요", desc: "API 테스트 허브 홈" },
  { path: "health", label: "헬스체크", desc: "GET /health, GET /" },
  { path: "auth", label: "인증", desc: "로그인·토큰·회원·RBAC" },
  { path: "messages", label: "재난문자", desc: "GET /api/v1/messages" },
  { path: "alert", label: "안내문자 파싱", desc: "POST /api/v1/alerts/parse" },
  { path: "search", label: "검색 요청", desc: "GET/POST /api/v1/search-requests" },
  { path: "disaster", label: "재난 알림", desc: "GET /api/v1/disaster-alerts" },
  { path: "result", label: "탐지 결과", desc: "GET /api/v1/detection-results" },
  { path: "cctv", label: "CCTV 분석", desc: "POST /api/v1/cctv/analyze" },
  { path: "chatbot", label: "챗봇", desc: "POST /api/v1/chatbot/chat" },
  { path: "admin", label: "관리자", desc: "회원 승인·목록" },
]

/** 현재 서브 경로에 맞는 페이지 제목 반환 (DevLayout 헤더용) */
export function devPageTitle(subPath) {
  const page = DEV_PAGES.find((p) => p.path === subPath)
  return page?.label ?? "Dev"
}
