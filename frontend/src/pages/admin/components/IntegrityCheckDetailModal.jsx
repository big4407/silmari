/** 정합성 검사 항목 — 이슈 상세 모달 */
import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { fetchIntegrityCheckIssues, saveBlobDownload } from '../../../api/client';
import {
  integrityFixLink,
  integrityStatusClass,
  integrityStatusLabel,
  integrityTargetLabel,
  issuesToCsvBlob,
} from '../integrityConfig';

export default function IntegrityCheckDetailModal({ open, check, onClose }) {
  const [issues, setIssues] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!open || !check) return;
    setCopied(false);
    setError('');
    const preview = check.samples ?? [];
    const needsFetch = check.issue_count > preview.length;

    if (!needsFetch) {
      setIssues(preview);
      setLoading(false);
      return;
    }

    let active = true;
    setLoading(true);
    setIssues(preview);
    fetchIntegrityCheckIssues(check.check_id)
      .then((data) => {
        if (!active) return;
        setIssues(data.issues ?? []);
      })
      .catch(() => {
        if (!active) return;
        setError('전체 이슈 목록을 불러오지 못했습니다. 샘플만 표시합니다.');
        setIssues(preview);
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, [open, check]);

  if (!open || !check) return null;

  const fixLink = integrityFixLink(check);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(issues.join('\n'));
      setCopied(true);
    } catch {
      setError('클립보드 복사에 실패했습니다.');
    }
  };

  const handleDownload = () => {
    const blob = issuesToCsvBlob(check, issues);
    saveBlobDownload(blob, `integrity_${check.check_id}.csv`);
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
          <h2>{check.label}</h2>
          <button type="button" className="admin-modal__close" onClick={onClose}>
            ×
          </button>
        </div>
        <div className="admin-modal__body">
          {error && <p className="admin-modal__error">{error}</p>}
          <dl className="admin-dl admin-dl--compact">
            <div>
              <dt>대상</dt>
              <dd>{integrityTargetLabel(check.target)}</dd>
            </div>
            <div>
              <dt>검사 내용</dt>
              <dd>{check.description}</dd>
            </div>
            <div>
              <dt>결과</dt>
              <dd>
                <span className={integrityStatusClass(check.status)}>
                  {integrityStatusLabel(check.status)}
                </span>
              </dd>
            </div>
            <div>
              <dt>이슈</dt>
              <dd>
                {check.issue_count}건
                {issues.length < check.issue_count && !loading
                  ? ` (표시 ${issues.length}건)`
                  : ''}
              </dd>
            </div>
          </dl>

          <div className="admin-modal__actions admin-modal__actions--start">
            <button
              type="button"
              className="admin-btn admin-btn--sm"
              onClick={handleCopy}
              disabled={!issues.length}
            >
              {copied ? '복사됨' : '목록 복사'}
            </button>
            <button
              type="button"
              className="admin-btn admin-btn--sm"
              onClick={handleDownload}
              disabled={!issues.length}
            >
              CSV 다운로드
            </button>
            {fixLink && (
              <Link
                to={`/admin/${fixLink.viewId}`}
                className="admin-btn admin-btn--sm admin-btn--primary"
                onClick={onClose}
              >
                {fixLink.label} →
              </Link>
            )}
          </div>

          {loading ? (
            <p className="admin-inline-status">전체 이슈 목록을 불러오는 중…</p>
          ) : issues.length === 0 ? (
            <p className="admin-inline-status">표시할 이슈가 없습니다.</p>
          ) : (
            <ul className="admin-issue-list">
              {issues.map((issue) => (
                <li key={issue}>
                  <code>{issue}</code>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}
