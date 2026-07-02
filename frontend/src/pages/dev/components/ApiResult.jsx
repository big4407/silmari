import "../DevCommon.css"

/** API 응답 본문을 pre 태그에 표시할 문자열로 변환 */
function formatBody(body) {
  if (body == null) return "(empty)"
  if (typeof body === "string") return body
  return JSON.stringify(body, null, 2)
}

/**
 * Dev 페이지 공통 결과 패널 — 요청 상태(로딩/성공/에러)와 JSON 응답을 표시
 */
export default function ApiResult({ status, data, error }) {
  // 상태바 색상·문구 결정
  const barClass =
    status === "loading"
      ? "dev-api-result__bar--loading"
      : status === "ok"
        ? "dev-api-result__bar--ok"
        : status === "err"
          ? "dev-api-result__bar--err"
          : "dev-api-result__bar--idle"

  const label =
    status === "loading"
      ? "요청 중…"
      : status === "ok"
        ? "성공"
        : status === "err"
          ? `오류${error?.status ? ` (${error.status})` : ""}`
          : "응답 대기"

  // 에러 시 FastAPI detail, 성공 시 data JSON 출력
  const body =
    status === "err"
      ? error?.detail ?? error?.message ?? formatBody(error)
      : formatBody(data)

  return (
    <div className="dev-api-result">
      <div className={`dev-api-result__bar ${barClass}`}>{label}</div>
      <pre className="dev-api-result__body">{body}</pre>
    </div>
  )
}

/** axios 에러에서 detail 추출 */
export function parseApiError(err) {
  const status = err.response?.status
  const detail = err.response?.data?.detail ?? err.message
  return { status, detail, message: typeof detail === "string" ? detail : JSON.stringify(detail) }
}
