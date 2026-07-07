import { useState } from "react"
import {
  collectMessages,
  fetchMessages,
  fetchMessage,
  createMessage,
  deleteMessage,
} from "../../api/messages_api"
import { API_V1 } from "../../api/client"
import ApiResult, { parseApiError } from "./components/ApiResult"
import "./DevCommon.css"

/** Dev — 재난문자 수집·조회·수동등록·삭제 테스트 */
export default function DevMessagesPage() {
  const [page, setPage] = useState("1")
  const [sn, setSn] = useState("")
  const [msgText, setMsgText] = useState("실종 신고: 홍길동, 남, 70세, 회색 상의")
  const [status, setStatus] = useState("idle")
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)

  /** API 호출 + 로딩/성공/에러 상태 갱신 (204 응답은 빈 본문 처리) */
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
      <h1 className="dev-page__title">재난문자</h1>
      <p className="dev-page__desc">메시지 수집·조회·수동 등록 API를 테스트합니다.</p>

      <div className="dev-section">
        <h2>수집 · 목록</h2>
        <div className="dev-form__row">
          <button
            type="button"
            className="dev-btn"
            onClick={() => run(() => collectMessages({ page_no: 1, num_of_rows: 5 }))}
          >
            POST {API_V1}/messages/collect
          </button>
          <button
            type="button"
            className="dev-btn dev-btn--secondary"
            onClick={() => run(() => fetchMessages({ page: Number(page) || 1, per_page: 10 }))}
          >
            GET {API_V1}/messages
          </button>
        </div>
        <div className="dev-form" style={{ marginTop: "0.75rem" }}>
          <label htmlFor="dev-msg-page">페이지</label>
          <input id="dev-msg-page" value={page} onChange={(e) => setPage(e.target.value)} />
        </div>
      </div>

      <div className="dev-section">
        <h2>단건 조회 · 삭제</h2>
        <div className="dev-form">
          <label htmlFor="dev-msg-sn">일련번호 (sn)</label>
          <input id="dev-msg-sn" value={sn} onChange={(e) => setSn(e.target.value)} placeholder="000001" />
          <div className="dev-form__row">
            <button
              type="button"
              className="dev-btn"
              disabled={!sn}
              onClick={() => run(() => fetchMessage(sn))}
            >
              GET {API_V1}/messages/{"{sn}"}
            </button>
            <button
              type="button"
              className="dev-btn dev-btn--danger"
              disabled={!sn}
              onClick={() => run(() => deleteMessage(sn))}
            >
              DELETE {API_V1}/messages/{"{sn}"}
            </button>
          </div>
        </div>
      </div>

      <div className="dev-section">
        <h2>수동 등록</h2>
        <div className="dev-form">
          <label htmlFor="dev-msg-text">메시지 내용</label>
          <textarea id="dev-msg-text" value={msgText} onChange={(e) => setMsgText(e.target.value)} />
          <button
            type="button"
            className="dev-btn"
            onClick={() =>
              run(() =>
                createMessage({
                  sn: `dev-${Date.now()}`,
                  msg_cn: msgText,
                  rcptn_rgn_nm: "서울특별시",
                }),
              )
            }
          >
            POST {API_V1}/messages/manual_input
          </button>
        </div>
        <ApiResult status={status} data={data} error={error} />
      </div>
    </>
  )
}
