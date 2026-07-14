/** 대시보드 플로팅 FAQ 챗봇 위젯 — ChatbotPage 와 별도 경량 UI */
import { useState } from 'react';
import './ChatbotWidget.css';

const FAQ = [
  {
    q: '실종자를 어떻게 검색하나요?',
    a: '지도에서 지역을 선택하고 검색기간을 설정한 뒤 검색 버튼을 눌러주세요.',
  },
  {
    q: '인상착의란?',
    a: '실종 당시 착용한 옷, 외형 특징 등의 정보입니다. 오른쪽 카드에서 확인할 수 있습니다.',
  },
];

export default function ChatbotWidget() {
  const [open, setOpen] = useState(false);
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState([
    {
      role: 'bot',
      text: '안녕하세요! 실마리 챗봇입니다. 궁금한 점을 입력해주세요.',
    },
  ]);

  const handleSend = () => {
    if (!input.trim()) return;
    const userMsg = input.trim();
    setMessages((prev) => [...prev, { role: 'user', text: userMsg }]);

    const matched = FAQ.find(
      (f) =>
        userMsg.includes(f.q.slice(0, 4)) || f.q.includes(userMsg.slice(0, 4)),
    );
    const reply = matched
      ? matched.a
      : '질문을 이해하지 못했습니다. 지도에서 지역을 선택하고 검색기간을 설정한 뒤 검색해 보세요.';

    setTimeout(() => {
      setMessages((prev) => [...prev, { role: 'bot', text: reply }]);
    }, 400);

    setInput('');
  };

  return (
    <div className="chatbot-widget">
      {open && (
        <div className="chatbot-panel">
          <div className="chatbot-panel__header">
            <span>챗봇</span>
            <button onClick={() => setOpen(false)} aria-label="닫기">
              ✕
            </button>
          </div>
          <div className="chatbot-panel__messages">
            {messages.map((msg, i) => (
              <div key={i} className={`chatbot-msg chatbot-msg--${msg.role}`}>
                {msg.text}
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="chatbot-input-row">
        <input
          className="chatbot-input"
          placeholder="질문창"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSend()}
          onFocus={() => setOpen(true)}
        />
        <button
          className="chatbot-btn"
          onClick={() => {
            setOpen(true);
            handleSend();
          }}
          aria-label="챗봇"
        >
          챗봇
        </button>
      </div>
    </div>
  );
}
