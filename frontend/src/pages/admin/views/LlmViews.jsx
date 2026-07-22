/** LLM 운영 뷰 — LLM 사용량 (연동) */

import { useEffect, useState } from 'react';

import PageHead from '../components/PageHead';
import { StatValue } from '../components/EmptyState';
import { LlmCallList } from '../components/LlmCallList';
import { LlmConversationModal } from '../components/LlmConversationModal';
import Pagination from '../components/Pagination';
import { adminPinnedPaginationStyle } from '../components/adminTableUtils';

import {
  getLlmCallList,
  getLlmConversation,
  getLlmUsageSummary,
} from '../../../api/llm_call_api';

// 요청대로 10줄
const PAGE_SIZE = 10;

export function LlmUsageView() {
  const [summary, setSummary] = useState({
    today_total: 0,
    total_translation: 0,
    total_chatbot: 0,
    total_alert_parse: 0,
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

        const [summaryData, listData] = await Promise.all([
          getLlmUsageSummary(),
          getLlmCallList({
            page,
            perPage: PAGE_SIZE,
          }),
        ]);

        setSummary({
          today_total: summaryData?.today_total ?? 0,
          total_translation: summaryData?.total_translation ?? 0,
          total_chatbot: summaryData?.total_chatbot ?? 0,
          total_alert_parse: summaryData?.total_alert_parse ?? 0,
        });
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
          <StatValue value={summary.today_total.toLocaleString()} unit="건" />
        </div>

        <div className="admin-stat">
          <div className="admin-label">인상착의 한영변환 (전체)</div>
          <StatValue
            value={summary.total_translation.toLocaleString()}
            unit="건"
          />
        </div>

        <div className="admin-stat">
          <div className="admin-label">챗봇 호출 (전체)</div>
          <StatValue value={summary.total_chatbot.toLocaleString()} unit="건" />
        </div>

        <div className="admin-stat">
          <div className="admin-label">안내문자 파싱 (전체)</div>
          <StatValue
            value={summary.total_alert_parse.toLocaleString()}
            unit="건"
          />
        </div>
      </div>

      <div style={adminPinnedPaginationStyle(PAGE_SIZE)}>
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
      </div>
      {!loading && !error && (
        <Pagination
          page={page}
          totalPages={totalPages}
          total={total}
          onPageChange={setPage}
        />
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
