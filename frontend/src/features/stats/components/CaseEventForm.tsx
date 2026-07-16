import { type FormEvent, useState } from 'react';

import { createCaseEvent } from '../api';
import type { CaseEvent, CaseEventType } from '../types';

interface CaseEventFormProps {
  onCreated: (event: CaseEvent) => void;
}

export function CaseEventForm({ onCreated }: CaseEventFormProps) {
  const [caseKey, setCaseKey] = useState('');
  const [searchId, setSearchId] = useState('');
  const [eventType, setEventType] = useState<CaseEventType>('FOUND');
  const [occurredAt, setOccurredAt] = useState('');
  const [actorName, setActorName] = useState('');
  const [actorRole, setActorRole] = useState('');
  const [region, setRegion] = useState('');
  const [locationText, setLocationText] = useState('');
  const [note, setNote] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);

    try {
      const created = await createCaseEvent({
        case_key: caseKey || undefined,
        source_search_id: searchId ? Number(searchId) : undefined,
        event_type: eventType,
        occurred_at: new Date(occurredAt).toISOString(),
        actor_name: actorName || undefined,
        actor_role: actorRole || undefined,
        region: region || undefined,
        location_text: locationText || undefined,
        note: note || undefined,
      });

      onCreated(created);
      setCaseKey('');
      setSearchId('');
      setOccurredAt('');
      setActorName('');
      setActorRole('');
      setRegion('');
      setLocationText('');
      setNote('');
    } catch (caughtError) {
      setError(
        caughtError instanceof Error
          ? caughtError.message
          : '이벤트 저장에 실패했습니다.',
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form className="stats-event-form" onSubmit={handleSubmit}>
      <div className="stats-form-grid">
        <label>
          사건 키
          <input
            value={caseKey}
            onChange={(event) => setCaseKey(event.target.value)}
            placeholder="예: CASE-2026-001"
          />
        </label>

        <label>
          연결 검색 ID
          <input
            type="number"
            min={1}
            value={searchId}
            onChange={(event) => setSearchId(event.target.value)}
            placeholder="사건 키가 없으면 필수"
          />
        </label>

        <label>
          기록 종류
          <select
            value={eventType}
            onChange={(event) => setEventType(event.target.value as CaseEventType)}
          >
            <option value="FOUND">대상자 발견</option>
            <option value="RESOLVED">사건 해결</option>
          </select>
        </label>

        <label>
          발생 일시
          <input
            type="datetime-local"
            value={occurredAt}
            onChange={(event) => setOccurredAt(event.target.value)}
            required
          />
        </label>

        <label>
          대상자명
          <input
            value={actorName}
            onChange={(event) => setActorName(event.target.value)}
          />
        </label>

        <label>
          대상자 역할
          <input
            value={actorRole}
            onChange={(event) => setActorRole(event.target.value)}
            placeholder="보호자, 관리자 등"
          />
        </label>

        <label>
          지역
          <input
            value={region}
            onChange={(event) => setRegion(event.target.value)}
            placeholder="예: 서울 관악구"
          />
        </label>

        <label>
          상세 장소
          <input
            value={locationText}
            onChange={(event) => setLocationText(event.target.value)}
          />
        </label>
      </div>

      <label className="stats-form-wide">
        처리 내용
        <textarea
          value={note}
          onChange={(event) => setNote(event.target.value)}
          rows={3}
        />
      </label>

      {error && <div className="stats-error">{error}</div>}

      <button
        type="submit"
        className="admin-btn admin-btn--primary"
        disabled={submitting || !occurredAt || (!caseKey && !searchId)}
      >
        {submitting ? '저장 중' : '이벤트 저장'}
      </button>
    </form>
  );
}
