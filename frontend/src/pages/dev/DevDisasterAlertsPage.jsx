import { useState } from "react"
import { fetchDisasterAlerts, API_V1 } from "../../api/client"
import ApiResult, { parseApiError } from "./components/ApiResult"
import DevPageHead from "./components/DevPageHead"
import "./DevCommon.css"

/** Dev — GET /api/v1/disaster-alerts (대시보드와 동일 API) */
export default function DevDisasterAlertsPage() {
  const [missingOnly, setMissingOnly] = useState(true)
  const [status, setStatus] = useState("idle")
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)

  /** missing_only 쿼리로 실종 관련 재난문자만 필터링 조회 */
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
      <DevPageHead title="재난 알림" desc="대시보드에서 사용하는 재난문자 목록 API입니다." />

      <div className="dev-section">
        <h2>GET {API_V1}/disaster-alerts</h2>
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
