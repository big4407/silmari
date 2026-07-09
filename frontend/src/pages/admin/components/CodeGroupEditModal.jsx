/** 코드 그룹 항목 수정 모달 */
import { useEffect, useState } from 'react';
import { updateCodeItem } from '../../../api/client';

function apiErrorMessage(err, fallback) {
  const detail = err?.response?.data?.detail;
  if (typeof detail === 'string') return detail;
  return fallback;
}

export default function CodeGroupEditModal({ open, item, onClose, onSaved }) {
  const [label, setLabel] = useState('');
  const [description, setDescription] = useState('');
  const [isActive, setIsActive] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!open || !item) return;
    setLabel(item.label ?? '');
    setDescription(item.description ?? '');
    setIsActive(item.is_active !== false);
    setError('');
  }, [open, item]);

  if (!open || !item) return null;

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!label.trim()) {
      setError('라벨을 입력하세요.');
      return;
    }
    setBusy(true);
    setError('');
    try {
      const saved = await updateCodeItem(item.groupKey, item.code, {
        label: label.trim(),
        description: description.trim() || null,
        is_active: isActive,
      });
      onSaved?.(saved);
      onClose();
    } catch (err) {
      setError(apiErrorMessage(err, '수정에 실패했습니다.'));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="admin-modal-overlay" role="presentation" onClick={onClose}>
      <div
        className="admin-modal"
        role="dialog"
        aria-modal="true"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="admin-modal__head">
          <h2>코드 수정</h2>
          <button type="button" className="admin-modal__close" onClick={onClose}>
            ×
          </button>
        </div>
        <form className="admin-modal__body" onSubmit={handleSubmit}>
          {error && <p className="admin-modal__error">{error}</p>}
          <div className="admin-fld">
            <label>그룹</label>
            <input value={item.groupLabel} disabled />
          </div>
          <div className="admin-fld">
            <label>코드값</label>
            <input value={item.code} disabled />
          </div>
          <div className="admin-fld">
            <label htmlFor="code_label">라벨</label>
            <input
              id="code_label"
              value={label}
              onChange={(e) => setLabel(e.target.value)}
              maxLength={100}
            />
          </div>
          <div className="admin-fld">
            <label htmlFor="code_desc">설명 (선택)</label>
            <input
              id="code_desc"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              maxLength={300}
            />
          </div>
          <label className="admin-check">
            <input
              type="checkbox"
              checked={isActive}
              onChange={(e) => setIsActive(e.target.checked)}
            />
            활성 (표시·선택에 사용)
          </label>
          <p className="admin-modal__hint">
            코드값 자체는 DB·enum 과 연결되어 변경할 수 없습니다. 라벨·활성
            여부만 수정됩니다.
          </p>
          <div className="admin-modal__actions">
            <button type="button" className="admin-btn" onClick={onClose} disabled={busy}>
              취소
            </button>
            <button
              type="submit"
              className="admin-btn admin-btn--primary"
              disabled={busy}
            >
              {busy ? '저장 중…' : '저장'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
