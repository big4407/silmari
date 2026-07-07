import { useState } from "react"
import { sendChatMessage } from "../../api/chatbot_api"
import { API_V1 } from "../../api/client"
import ApiResult, { parseApiError } from "./components/ApiResult"
import "./DevCommon.css"

/** Dev — POST /api/chatbot/chat (세션 기반 대화) */
export default function DevChatbotPage() {
  const [sessionId, setSessionId] = useState(() => `dev-${Date.now()}`)
  const [message, setMessage] = useState("서울 종로구에서 실종된 70대 남성을 찾고 있어요.")
  const [status, setStatus] = useState("idle")
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)

  /** 메시지 전송 — 서버가 session_id를 갱신하면 로컬 state 동기화 */
  const send = async () => {
    setStatus("loading")
    setError(null)
    try {
      const result = await sendChatMessage({ sessionId, message })
      setData(result)
      if (result.session_id) setSessionId(result.session_id)
      setStatus("ok")
    } catch (err) {
      setError(parseApiError(err))
      setStatus("err")
    }
  }

  return (
    <>
      <h1 className="dev-page__title">챗봇</h1>
      <p className="dev-page__desc">POST {API_V1}/chatbot/chat — 세션 ID로 대화를 이어갑니다.</p>

      <div className="dev-section">
        <h2>메시지 전송</h2>
        <div className="dev-form">
          <label htmlFor="dev-chat-session">세션 ID</label>
          <input
            id="dev-chat-session"
            value={sessionId}
            onChange={(e) => setSessionId(e.target.value)}
          />
          <label htmlFor="dev-chat-msg">메시지</label>
          <textarea
            id="dev-chat-msg"
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            rows={4}
          />
          <div className="dev-form__row">
            <button
              type="button"
              className="dev-btn"
              disabled={!message.trim()}
              onClick={send}
            >
              전송
            </button>
            <button
              type="button"
              className="dev-btn dev-btn--secondary"
              onClick={() => setSessionId(`dev-${Date.now()}`)}
            >
              새 세션
            </button>
          </div>
        </div>
        <ApiResult status={status} data={data} error={error} />
      </div>
    </>
  )
}
