/** 챗봇 UI — 세션 복원 + 메시지 전송, 검색 삽입 시 스토어 연동 */
import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import './ChatbotPage.css';
import {
  sendChatMessage,
  getChatSession,
  deleteChatSession,
} from '../api/chatbot_api';
import { useDetectionStore } from '../store/useDetectionStore';
import SearchProgressBar from '../components/SearchProgressBar';

export default function ChatbotPage() {
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState([]);
  const [sending, setSending] = useState(false);
  const [searched, setSearched] = useState(false);
  const [sessionId, setSessionId] = useState(() =>
    localStorage.getItem('chatbot_session_id'),
  );
  const setActiveSearch = useDetectionStore((state) => state.setActiveSearch);
  const navigate = useNavigate();
  const inputRef = useRef(null);

  const updateSessionId = (newSessionId) => {
    if (newSessionId) {
      localStorage.setItem('chatbot_session_id', newSessionId);
    } else {
      localStorage.removeItem('chatbot_session_id');
    }

    setSessionId(newSessionId);
  };

  const handleSend = async () => {
    if (!input.trim() || sending) return;

    const userMsg = input.trim();

    setMessages((prev) => [...prev, { role: 'user', text: userMsg }]);
    setInput('');
    setSending(true);

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
        setSearched(true);
      }
      setMessages((prev) => [...prev, { role: 'bot', text: data.response }]);
    } catch (error) {
      console.error(error);

      setMessages((prev) => [
        ...prev,
        { role: 'bot', text: '챗봇 서버와 연결할 수 없습니다.' },
      ]);
    } finally {
      setSending(false);
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

  // 검색이 완료되었을 경우 일정 시간 후 search-results로 redirect
  useEffect(() => {
    if (!searched) return;

    const timer = setTimeout(() => {
      navigate('/search-results');
    }, 1500); // 1.5초 후 이동

    return () => clearTimeout(timer);
  }, [searched, navigate]);

  // 챗봇으로부터 메시지를 받으면 바로 채팅창에 focus하도록
  useEffect(() => {
    if (!sending&&!searched) {
      inputRef.current?.focus();
    }
  }, [sending]);

  // 챗봇 세션 초기화 버튼을 눌렀을 때 실행
  const handleResetSession = async () => {
    try {
      await deleteChatSession();

      localStorage.removeItem('chatbot_session_id');
      window.location.reload();
    } catch (error) {
      console.error('챗봇 세션 초기화 실패:', error);

      setMessages((prev) => [
        ...prev,
        {
          role: 'bot',
          text: '챗봇 세션을 초기화하지 못했습니다.',
        },
      ]);
    }
  };

  return (
    <div className="chatbot-page">
      <div className="chatbot-page__panel">
        <div className="chatbot-page__chrome">
          <span className="chatbot-page__dot" />
          <span className="chatbot-page__dot" />
          <span className="chatbot-page__dot" />
          <span className="chatbot-page__title">챗봇 검색</span>
        </div>
        <button
          type="button"
          className="admin-btn"
          onClick={handleResetSession}
        >
          세션 초기화
        </button>
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

          <div className="chatbot-page__progress">
            <SearchProgressBar
              visible={sending}
              label="분석 중… 입력 내용을 처리하고 있습니다."
            />
          </div>

          <div className="chatbot-page__input-row">
            <input
              ref={inputRef}
              className="chatbot-page__input"
              placeholder="지역, 일자, 인상착의 등의 실종자 정보를 입력하세요"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSend()}
              disabled={sending||searched}
            />
            <button
              type="button"
              className="chatbot-page__send"
              onClick={handleSend}
              disabled={sending || !input.trim()}
            >
              {sending ? '전송 중…' : '전송'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
