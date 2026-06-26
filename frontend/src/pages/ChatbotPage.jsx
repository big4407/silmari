import { useEffect, useRef, useState } from "react"
import "./ChatbotPage.css"

const FAQ = [
  {
    keys: ["실종자", "검색", "어떻게"],
    a: "실종자 검색 탭에서 지도로 지역을 선택하고, 상단에서 기간·문자 내용을 설정한 뒤 「안내문자 조회」를 눌러 주세요.",
  },
  {
    keys: ["인상착의", "인상", "착의"],
    a: "실종 당시 착용한 옷·외형 정보입니다. 안내문자 본문이나 검색 조건의 「문자 내용」에 활용할 수 있습니다.",
  },
  {
    keys: ["안내문자", "조회", "어디서"],
    a: "「실종자 검색」 탭 오른쪽 「실종 안내문자」 목록에서 조회합니다. 상단 「안내문자 조회」 버튼으로 최근 안내문자를 불러올 수 있습니다.",
  },
]

const SUGGESTED_PROMPTS = [
  { label: "실종자 검색 방법", prompt: "실종자를 어떻게 검색하나요?" },
  { label: "인상착의란?", prompt: "인상착의란 무엇인가요?" },
  { label: "안내문자 조회 방법", prompt: "안내문자는 어디서 조회하나요?" },
]

const WELCOME =
  "안녕하세요! 실마리 챗봇입니다. 실종자 검색·안내문자 조회 방법 등을 안내해 드립니다. 아래 예시를 눌러 보셔도 됩니다."

function findFaqReply(text) {
  const normalized = text.trim().toLowerCase()
  for (const item of FAQ) {
    if (item.keys.some((key) => normalized.includes(key))) {
      return item.a
    }
  }
  return null
}

function BotAvatar() {
  return (
    <span className="chatbot-page__avatar chatbot-page__avatar--bot" aria-hidden="true">
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
        <path
          d="M8 10h.01M12 10h.01M16 10h.01M21 12c0 4.418-4.03 8-9 8a9.86 9.86 0 01-4-.8L3 20l1.2-3.6C3.4 15.1 3 13.6 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
          stroke="currentColor"
          strokeWidth="1.8"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
    </span>
  )
}

export default function ChatbotPage() {
  const [input, setInput] = useState("")
  const [messages, setMessages] = useState([{ role: "bot", text: WELCOME }])
  const [showSuggestions, setShowSuggestions] = useState(true)
  const messagesEndRef = useRef(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  const sendMessage = (text) => {
    const userMsg = text.trim()
    if (!userMsg) return

    setShowSuggestions(false)
    setMessages((prev) => [...prev, { role: "user", text: userMsg }])

    const reply =
      findFaqReply(userMsg) ??
      "아직 해당 질문은 준비 중입니다. 「실종자 검색」 탭에서 지역·기간을 설정하고 조회해 보시거나, 다른 키워드로 물어봐 주세요."

    window.setTimeout(() => {
      setMessages((prev) => [...prev, { role: "bot", text: reply }])
    }, 350)

    setInput("")
  }

  const handleSend = () => sendMessage(input)

  const handleChipClick = (prompt) => sendMessage(prompt)

  return (
    <div className="chatbot-page">
      <div className="chatbot-page__panel">
        <div className="chatbot-page__messages">
          {messages.map((msg, i) => (
            <div
              key={i}
              className={`chatbot-page__row chatbot-page__row--${msg.role}`}
            >
              {msg.role === "bot" && <BotAvatar />}
              <div className={`chatbot-page__msg chatbot-page__msg--${msg.role}`}>
                {msg.text}
              </div>
            </div>
          ))}

          {showSuggestions && (
            <div className="chatbot-page__suggestions">
              {SUGGESTED_PROMPTS.map((item) => (
                <button
                  key={item.label}
                  type="button"
                  className="chatbot-page__chip"
                  onClick={() => handleChipClick(item.prompt)}
                >
                  {item.label}
                </button>
              ))}
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        <div className="chatbot-page__input-row">
          <input
            className="chatbot-page__input"
            placeholder="질문을 입력하세요"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault()
                handleSend()
              }
            }}
            aria-label="챗봇 질문 입력"
          />
          <button
            type="button"
            className="chatbot-page__send"
            onClick={handleSend}
            aria-label="전송"
          >
            <span>전송</span>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden="true">
              <path
                d="M5 12h14M13 6l6 6-6 6"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </button>
        </div>
      </div>
    </div>
  )
}
