import "../DevCommon.css"

function formatBody(body) {
  if (body == null) return "(empty)"
  if (typeof body === "string") return body
  return JSON.stringify(body, null, 2)
}

export default function ApiResult({ status, data, error }) {
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
