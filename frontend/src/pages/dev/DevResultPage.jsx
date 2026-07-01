import { useState } from "react"
import {
  fetchSearchResults,
  fetchSearchResultDetail,
  fetchMissingList,
  deleteSearchResult,
} from "../../api/client"
import ApiResult, { parseApiError } from "./components/ApiResult"
import "./DevCommon.css"

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
      <h1 className="dev-page__title">탐지 결과</h1>
      <p className="dev-page__desc">CCTV 분석 후 저장되는 검색 결과 API입니다.</p>

      <div className="dev-section">
        <h2>목록 · 상세</h2>
        <div className="dev-form__row">
          <button
            type="button"
            className="dev-btn"
            onClick={() => run(() => fetchSearchResults({ limit: 10 }))}
          >
            GET /api/result/search
          </button>
          <button
            type="button"
            className="dev-btn dev-btn--secondary"
            onClick={() => run(() => fetchMissingList())}
          >
            GET /api/result/list
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
              GET /api/result/search/{"{id}"}
            </button>
            <button
              type="button"
              className="dev-btn dev-btn--danger"
              disabled={!resultId}
              onClick={() => run(() => deleteSearchResult(resultId))}
            >
              DELETE /api/result/search/{"{id}"}
            </button>
          </div>
        </div>
        <ApiResult status={status} data={data} error={error} />
      </div>
    </>
  )
}
