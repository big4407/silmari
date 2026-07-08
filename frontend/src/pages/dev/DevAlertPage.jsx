import { useState } from "react"
import devClient from "../../api/devClient"
import { API_V1 } from "../../api/client"
import ApiResult, { parseApiError } from "./components/ApiResult"
import DevPageHead from "./components/DevPageHead"
import "./DevCommon.css"

const SAMPLE_TEXT =
  "실종자 안내\n이름: 김철수\n나이: 75세\n성별: 남\n착의: 검은 패딩, 청바지\n실종장소: 서울 종로구"

/** Dev — POST /api/v1/alerts/parse (LLM으로 안내문자 → 구조화 JSON) */
export default function DevAlertPage() {
  const [text, setText] = useState(SAMPLE_TEXT)
  const [status, setStatus] = useState("idle")
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)

  /** 안내문자 원문을 JSON(이름·나이·착의 등)으로 파싱 */
  const parse = async () => {
    setStatus("loading")
    setError(null)
    try {
      const { data: res } = await devClient.post(`${API_V1}/alerts/parse`, { text })
      setData(res)
      setStatus("ok")
    } catch (err) {
      setError(parseApiError(err))
      setStatus("err")
    }
  }

  return (
    <>
      <DevPageHead title="안내문자 파싱" desc="LLM으로 안내문자에서 인상착의를 구조화합니다." />

      <div className="dev-section">
        <h2>POST {API_V1}/alerts/parse</h2>
        <div className="dev-form">
          <label htmlFor="dev-alert-text">안내문자 원문</label>
          <textarea
            id="dev-alert-text"
            value={text}
            onChange={(e) => setText(e.target.value)}
            rows={8}
          />
          <button type="button" className="dev-btn" disabled={!text.trim()} onClick={parse}>
            파싱 실행
          </button>
        </div>
        <ApiResult status={status} data={data} error={error} />
      </div>
    </>
  )
}
