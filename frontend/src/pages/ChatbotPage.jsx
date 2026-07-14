/** 챗봇 UI — 현재 로컬 목 응답만 (향후 LLM·비전 API 연동 예정) */
import { useState, useEffect } from 'react';
import './ChatbotPage.css';
import { sendChatMessage, getChatSession } from '../api/chatbot_api';
import { useDetectionStore } from '../store/useDetectionStore';
export default function ChatbotPage() {
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState([]);
  const [sessionId, setSessionId] = useState(() =>
    localStorage.getItem('chatbot_session_id'),
  );
  const setActiveSearch = useDetectionStore((state) => state.setActiveSearch);
  const updateSessionId = (newSessionId) => {
    if (newSessionId) {
      localStorage.setItem('chatbot_session_id', newSessionId);
    } else {
      localStorage.removeItem('chatbot_session_id');
    }

    setSessionId(newSessionId);
  };
  const handleSend = async () => {
    if (!input.trim()) return;

    const userMsg = input.trim();

    setMessages((prev) => [...prev, { role: 'user', text: userMsg }]);
    setInput('');

    try {
      const data = await sendChatMessage({
        sessionId: sessionId,
        message: userMsg,
      });
      console.log('챗봇 응답:', data);
      updateSessionId(data.session_id);
      if (data.search_inserted && data.search_id) {
        setActiveSearch({
          searchResultId: data.search_id,
        });
      }
      setMessages((prev) => [...prev, { role: 'bot', text: data.response }]);
    } catch (error) {
      console.error(error);

      setMessages((prev) => [
        ...prev,
        { role: 'bot', text: '챗봇 서버와 연결할 수 없습니다.' },
      ]);
    }
  };

  // 원래 세션이 있었을 경우, 메시지 내역을 불러온다.
  // 세션이 없을 경우 세션을 먼저 생성하고 불러온다. 만약에 오류가 발생할 경우 챗봇 세션을 불러오지 못했다는 메시지를 출력한다.
  useEffect(() => {
    const loadMessages = async () => {
      try {
        const data = await getChatSession(sessionId);

        updateSessionId(data.session_id);

        setMessages(
          data.messages.map((m) => ({
            role: m.role === 'assistant' ? 'bot' : 'user',
            text: m.content,
          })),
        );
      } catch (err) {
        setMessages([
          {
            role: 'bot',
            text: '챗봇 세션을 불러오지 못했습니다.',
          },
        ]);
        console.log(err);
      }
    };

    loadMessages();
  }, []);

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
              <div
                key={i}
                className={`chatbot-page__msg chatbot-page__msg--${msg.role}`}
              >
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
              onKeyDown={(e) => e.key === 'Enter' && handleSend()}
            />
            <button
              type="button"
              className="chatbot-page__send"
              onClick={handleSend}
            >
              전송
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
