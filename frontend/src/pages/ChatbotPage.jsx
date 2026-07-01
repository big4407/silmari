/** 챗봇 UI — 현재 로컬 목 응답만 (향후 LLM·비전 API 연동 예정) */
import { useState } from "react"
import "./ChatbotPage.css"
import { sendChatMessage } from "../api/chatbot_api"

export default function ChatbotPage() {
  const [input, setInput] = useState("")
  const [messages, setMessages] = useState([
    {
      role: "bot",
      text: "안녕하세요! 실마리 챗봇입니다. 사진이나 인상착의를 입력해 주세요.",
    },
  ])
  const getSessionId = () => {
    let sessionId = localStorage.getItem("chatbot_session_id")

    if (!sessionId) {
      sessionId = crypto.randomUUID()
      localStorage.setItem("chatbot_session_id", sessionId)
    }

    return sessionId
  }

  const handleSend = async () => {
  if (!input.trim()) return

  const userMsg = input.trim()

  setMessages((prev) => [...prev, { role: "user", text: userMsg }])
  setInput("")

  try {
    const data = await sendChatMessage({
      sessionId: getSessionId(),
      message: userMsg,
    })

    setMessages((prev) => [
      ...prev,
      { role: "bot", text: data.response },
    ])
  } catch (error) {
    console.error(error)

    setMessages((prev) => [
      ...prev,
      { role: "bot", text: "챗봇 서버와 연결할 수 없습니다." },
    ])
  }
}

  return (
    <div className="chatbot-page">
      <div className="chatbot-page__panel">
        <div className="chatbot-page__chrome">
          <span className="chatbot-page__dot" />
          <span className="chatbot-page__dot" />
          <span className="chatbot-page__dot" />
          <span className="chatbot-page__title">챗봇 검색</span>
        </div>

        <div className="chatbot-page__body">
          <div className="chatbot-page__messages">
            {messages.map((msg, i) => (
              <div key={i} className={`chatbot-page__msg chatbot-page__msg--${msg.role}`}>
                {msg.text}
              </div>
            ))}
          </div>

          <div className="chatbot-page__input-row">
            <input
              className="chatbot-page__input"
              placeholder="사진 또는 특징을 입력하세요"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSend()}
            />
            <button type="button" className="chatbot-page__send" onClick={handleSend}>
              전송
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
