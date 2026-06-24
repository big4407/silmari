import { useState } from "react"
import "./ChatbotPage.css"

const FAQ = [
  { q: "실종자를 어떻게 검색하나요?", a: "지도에서 지역을 선택하고 검색기간을 설정한 뒤 검색 버튼을 눌러주세요." },
  { q: "인상착의란?", a: "실종 당시 착용한 옷, 외형 특징 등의 정보입니다. 실종자 검색 탭에서 확인할 수 있습니다." },
]

export default function ChatbotPage() {
  const [input, setInput] = useState("")
  const [messages, setMessages] = useState([
    { role: "bot", text: "안녕하세요! 실마리 챗봇입니다. 궁금한 점을 입력해주세요." },
  ])

  const handleSend = () => {
    if (!input.trim()) return
    const userMsg = input.trim()
    setMessages((prev) => [...prev, { role: "user", text: userMsg }])

    const matched = FAQ.find(
      (f) => userMsg.includes(f.q.slice(0, 4)) || f.q.includes(userMsg.slice(0, 4)),
    )
    const reply = matched
      ? matched.a
      : "질문을 이해하지 못했습니다. 실종자 검색 탭에서 지역을 선택하고 검색해 보세요."

    setTimeout(() => {
      setMessages((prev) => [...prev, { role: "bot", text: reply }])
    }, 400)

    setInput("")
  }

  return (
    <div className="chatbot-page">
      <div className="chatbot-page__panel">
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
            placeholder="질문을 입력하세요"
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
  )
}
