import { useState } from "react"
import {
  fetchSearchResults,
  fetchSearchResultDetail,
  fetchMissingList,
  deleteSearchResult,
  API_V1,
} from "../../api/client"
import ApiResult, { parseApiError } from "./components/ApiResult"
import DevPageHead from "./components/DevPageHead"
import "./DevCommon.css"

/** Dev — CCTV 분석 결과(detection-results) 목록·상세·삭제 테스트 */
export default function DevResultPage() {
  const [resultId, setResultId] = useState("")
  const [status, setStatus] = useState("idle")
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)

  const run = async (fn) => {
    setStatus("loading")
    setError(null)
    try {
      const result = await fn()
      setData(result ?? { message: "완료 (204 No Content)" })
      setStatus("ok")
    } catch (err) {
      setError(parseApiError(err))
      setStatus("err")
    }
  }

  return (
    <>
      <DevPageHead title="탐지 결과" desc="CCTV 분석 후 저장되는 검색 결과 API입니다." />

      <div className="dev-section">
        <h2>목록 · 상세</h2>
        <div className="dev-form__row">
          <button
            type="button"
            className="dev-btn"
            onClick={() => run(() => fetchSearchResults({ limit: 10 }))}
          >
            GET {API_V1}/detection-results
          </button>
          <button
            type="button"
            className="dev-btn dev-btn--secondary"
            onClick={() => run(() => fetchMissingList())}
          >
            GET {API_V1}/detection-results/list
          </button>
        </div>
        <div className="dev-form" style={{ marginTop: "0.75rem" }}>
          <label htmlFor="dev-result-id">결과 ID</label>
          <input id="dev-result-id" value={resultId} onChange={(e) => setResultId(e.target.value)} />
          <div className="dev-form__row">
            <button
              type="button"
              className="dev-btn"
              disabled={!resultId}
              onClick={() => run(() => fetchSearchResultDetail(resultId))}
            >
              GET {API_V1}/detection-results/{"{id}"}
            </button>
            <button
              type="button"
              className="dev-btn dev-btn--danger"
              disabled={!resultId}
              onClick={() => run(() => deleteSearchResult(resultId))}
            >
              DELETE {API_V1}/detection-results/{"{id}"}
            </button>
          </div>
        </div>
        <ApiResult status={status} data={data} error={error} />
      </div>
    </>
  )
}
