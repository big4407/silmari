/** 보존 정책 드라이런 미리보기 모달 */
import { useState } from 'react';
import { saveBlobDownload } from '../../../api/client';

const ACTION_LABELS = {
  delete: '삭제',
  archive: '보관',
  anonymize: '익명화',
};

function csvEscape(value) {
  const text = String(value ?? '');
  if (/[",\n\r]/.test(text)) return `"${text.replace(/"/g, '""')}"`;
  return text;
}

function dryRunToCsvBlob(items) {
  const header = [
    'policy_id',
    'data_label',
    'expiry_action',
    'expired_count',
    'sample',
  ];
  const lines = [header.join(',')];
  for (const item of items) {
    if (!item.samples?.length) {
      lines.push(
        [item.policy_id, item.data_label, item.expiry_action, item.expired_count, '']
          .map(csvEscape)
          .join(','),
      );
      continue;
    }
    for (const sample of item.samples) {
      lines.push(
        [item.policy_id, item.data_label, item.expiry_action, item.expired_count, sample]
          .map(csvEscape)
          .join(','),
      );
    }
  }
  return new Blob(['\ufeff', lines.join('\n')], { type: 'text/csv;charset=utf-8' });
}

export default function RetentionDryRunModal({
  open,
  items,
  title,
  loading,
  error,
  onClose,
}) {
  const [copied, setCopied] = useState(false);

  if (!open) return null;

  const total = items.reduce((sum, item) => sum + (item.expired_count ?? 0), 0);
  const activeTotal = items
    .filter((item) => item.is_active)
    .reduce((sum, item) => sum + (item.expired_count ?? 0), 0);

  const allSamples = items.flatMap((item) =>
    (item.samples ?? []).map((sample) => ({
      label: item.data_label,
      action: item.expiry_action,
      sample,
    })),
  );

  const handleCopy = async () => {
    const text = items
      .map((item) => {
        const header = `[${item.data_label}] ${ACTION_LABELS[item.expiry_action] || item.expiry_action} 대상 ${item.expired_count}건`;
        const lines = (item.samples ?? []).map((s) => `  - ${s}`);
        return [header, ...lines].join('\n');
      })
      .join('\n\n');
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
    } catch {
      /* ignore */
    }
  };

  const handleDownload = () => {
    saveBlobDownload(dryRunToCsvBlob(items), 'retention_dry_run.csv');
  };

  return (
    <div className="admin-modal-overlay" role="presentation" onClick={onClose}>
      <div
        className="admin-modal admin-modal--wide"
        role="dialog"
        aria-modal="true"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="admin-modal__head">
          <h2>{title || '보존 정책 드라이런'}</h2>
          <button type="button" className="admin-modal__close" onClick={onClose}>
            ×
          </button>
        </div>
        <div className="admin-modal__body">
          {loading && (
            <p className="admin-inline-status">만료 대상을 집계하는 중…</p>
          )}
          {error && <p className="admin-modal__error">{error}</p>}
          {!loading && !error && (
            <>
              <p className="admin-inline-ok">
                보존 기간 초과 — 전체 {total.toLocaleString()}건
                {activeTotal !== total
                  ? ` (적용 중 정책 기준 ${activeTotal.toLocaleString()}건)`
                  : ''}
              </p>
              <div className="admin-modal__actions admin-modal__actions--start">
                <button
                  type="button"
                  className="admin-btn admin-btn--sm"
                  onClick={handleCopy}
                  disabled={!items.length}
                >
                  {copied ? '복사됨' : '목록 복사'}
                </button>
                <button
                  type="button"
                  className="admin-btn admin-btn--sm"
                  onClick={handleDownload}
                  disabled={!items.length}
                >
                  CSV 다운로드
                </button>
              </div>
              <div className="admin-dry-run-list">
                {items.map((item) => (
                  <div key={item.policy_id} className="admin-dry-run-item">
                    <div className="admin-dry-run-item__head">
                      <strong>{item.data_label}</strong>
                      <span className="admin-pill admin-pill--muted">
                        {ACTION_LABELS[item.expiry_action] || item.expiry_action}
                      </span>
                      <span>
                        {item.expired_count.toLocaleString()}건
                        {!item.is_active ? ' · 중지' : ''}
                      </span>
                    </div>
                    {item.skipped_reason && (
                      <p className="admin-cell-sub">{item.skipped_reason}</p>
                    )}
                    {item.samples?.length > 0 ? (
                      <ul className="admin-issue-list">
                        {item.samples.map((sample) => (
                          <li key={`${item.policy_id}-${sample}`}>
                            <code>{sample}</code>
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <p className="admin-cell-sub">만료 대상 없음</p>
                    )}
                  </div>
                ))}
              </div>
              {allSamples.length === 0 && items.length > 0 && (
                <p className="admin-footnote">모든 정책에서 만료 대상이 없습니다.</p>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
