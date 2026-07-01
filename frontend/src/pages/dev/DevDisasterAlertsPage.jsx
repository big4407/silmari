import { useState } from "react"
import { fetchDisasterAlerts } from "../../api/client"
import ApiResult, { parseApiError } from "./components/ApiResult"
import "./DevCommon.css"

export default function DevDisasterAlertsPage() {
  const [missingOnly, setMissingOnly] = useState(true)
  const [status, setStatus] = useState("idle")
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)

  const load = async () => {
    setStatus("loading")
    setError(null)
    try {
      const result = await fetchDisasterAlerts({ missing_only: missingOnly })
      setData(result)
      setStatus("ok")
    } catch (err) {
      setError(parseApiError(err))
      setStatus("err")
    }
  }

  return (
    <>
      <h1 className="dev-page__title">재난 알림</h1>
      <p className="dev-page__desc">대시보드에서 사용하는 재난문자 목록 API입니다.</p>

      <div className="dev-section">
        <h2>GET /api/alerts/list</h2>
        <div className="dev-form">
          <label>
            <input
              type="checkbox"
              checked={missingOnly}
              onChange={(e) => setMissingOnly(e.target.checked)}
            />{" "}
            missing_only (실종 관련만)
          </label>
          <button type="button" className="dev-btn" onClick={load}>
            목록 조회
          </button>
        </div>
        <ApiResult status={status} data={data} error={error} />
      </div>
    </>
  )
}
