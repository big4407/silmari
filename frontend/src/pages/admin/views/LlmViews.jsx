/** LLM 운영 뷰 — LLM 사용량 (연동) */

import { useEffect, useState } from 'react';

import PageHead from '../components/PageHead';
import { StatValue } from '../components/EmptyState';
import { LlmCallList } from '../components/LlmCallList';
import { LlmConversationModal } from '../components/LlmConversationModal';

import {
  getLlmCallList,
  getLlmConversation,
  // getLlmUsageSummary,
} from '../../../api/llm_call_api';

const PAGE_SIZE = 10;

export function LlmUsageView() {
  const [summary, setSummary] = useState({
    total_calls: 0,
    translation_calls: 0,
    chatbot_calls: 0,
    success_rate: 0,
  });

  const [items, setItems] = useState([]);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const [selectedConversation, setSelectedConversation] = useState(null);
  const [conversationOpen, setConversationOpen] = useState(false);
  const [conversationLoading, setConversationLoading] = useState(false);

  const totalPages = Math.ceil(total / PAGE_SIZE);

  useEffect(() => {
    const loadLlmData = async () => {
      try {
        setLoading(true);
        setError('');

        const [listData] = await Promise.all([
          // getLlmUsageSummary(),
          getLlmCallList({
            page,
            perPage: PAGE_SIZE,
          }),
        ]);

        // setSummary({
        //   total_calls: summaryData.total_calls ?? 0,
        //   translation_calls: summaryData.translation_calls ?? 0,
        //   chatbot_calls: summaryData.chatbot_calls ?? 0,
        //   success_rate: summaryData.success_rate ?? 0,
        // });
        // console.log('listData', listData);
        if (listData) {
          setItems(listData.items ?? []);
          setTotal(listData.total ?? 0);
        }
      } catch (err) {
        console.error(err);

        setError(
          err instanceof Error
            ? err.message
            : 'LLM 호출 내역을 불러오지 못했습니다.',
        );
      } finally {
        setLoading(false);
      }
    };

    loadLlmData();
  }, [page]);

  const handleOpenConversation = async (chatbotSessionId) => {
    try {
      setConversationOpen(true);
      setConversationLoading(true);
      setSelectedConversation(null);

      const data = await getLlmConversation(chatbotSessionId);

      setSelectedConversation(data);
    } catch (err) {
      console.error(err);
      setSelectedConversation(null);
    } finally {
      setConversationLoading(false);
    }
  };

  const handleCloseConversation = () => {
    setConversationOpen(false);
    setSelectedConversation(null);
  };

  return (
    <>
      <PageHead
        viewId="llm-usage"
        desc="LLM 호출 기록과 사용량, 비용 등을 확인합니다."
      />

      <div className="admin-stat-grid">
        <div className="admin-stat">
          <div className="admin-label">오늘 총 호출</div>
          <StatValue value={summary.total_calls.toLocaleString()} unit="건" />
        </div>

        <div className="admin-stat">
          <div className="admin-label">인상착의 한영변환</div>
          <StatValue
            value={summary.translation_calls.toLocaleString()}
            unit="건"
          />
        </div>

        <div className="admin-stat">
          <div className="admin-label">챗봇 호출</div>
          <StatValue value={summary.chatbot_calls.toLocaleString()} unit="건" />
        </div>

        <div className="admin-stat admin-stat--green">
          <div className="admin-label">성공률</div>
          <StatValue value={summary.success_rate.toFixed(1)} unit="%" />
        </div>
      </div>

      <div className="admin-card admin-table-wrap">
        <div className="admin-card-h">LLM 호출 내역</div>

        {loading && <div className="admin-loading">불러오는 중...</div>}

        {error && <div className="admin-error">{error}</div>}

        {!loading && !error && (
          <LlmCallList
            items={items}
            onOpenConversation={handleOpenConversation}
          />
        )}

        {!loading && !error && totalPages > 1 && (
          <div className="admin-pagination">
            <button
              className="admin-btn"
              type="button"
              disabled={page === 1}
              onClick={() => setPage((prev) => Math.max(prev - 1, 1))}
            >
              이전
            </button>

            <span>
              {page} / {totalPages}
            </span>

            <button
              className="admin-btn"
              type="button"
              disabled={page === totalPages}
              onClick={() => setPage((prev) => Math.min(prev + 1, totalPages))}
            >
              다음
            </button>
          </div>
        )}
      </div>

      <LlmConversationModal
        open={conversationOpen}
        conversation={selectedConversation}
        loading={conversationLoading}
        onClose={handleCloseConversation}
      />
    </>
  );
}
