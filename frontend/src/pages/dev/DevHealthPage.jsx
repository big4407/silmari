import { useState } from "react"
import devClient from "../../api/devClient"
import ApiResult, { parseApiError } from "./components/ApiResult"
import DevPageHead from "./components/DevPageHead"
import "./DevCommon.css"

export default function DevHealthPage() {
  const [status, setStatus] = useState("idle")
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)

  const call = async (path) => {
    setStatus("loading")
    setError(null)
    try {
      const res = await devClient.get(path)
      setData(res.data)
      setStatus("ok")
    } catch (err) {
      setError(parseApiError(err))
      setStatus("err")
    }
  }

  return (
    <>
      <DevPageHead title="헬스체크" desc="서버 기동 여부를 확인합니다." />

      <div className="dev-section">
        <h2>엔드포인트</h2>
        <div className="dev-form__row">
          <button type="button" className="dev-btn" onClick={() => call("/health")}>
            GET /health
          </button>
          <button type="button" className="dev-btn dev-btn--secondary" onClick={() => call("/")}>
            GET /
          </button>
        </div>
        <ApiResult status={status} data={data} error={error} />
      </div>
    </>
  )
}
