/** 행정구역 등록·수정 모달 */
import { useEffect, useState } from 'react';
import {
  createRegion,
  fetchRegionOptions,
  updateRegion,
} from '../../../api/client';

const EMPTY_FORM = {
  region_code: '',
  specific_name: '',
  full_name: '',
  parent_code: '',
};

function apiErrorMessage(err, fallback) {
  const detail = err?.response?.data?.detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) return detail.map((d) => d.msg).join(', ');
  return fallback;
}

export default function RegionFormModal({
  open,
  mode = 'create',
  initial,
  onClose,
  onSaved,
}) {
  const [form, setForm] = useState(EMPTY_FORM);
  const [options, setOptions] = useState([]);
  const [loadingOptions, setLoadingOptions] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  const isEdit = mode === 'edit';

  useEffect(() => {
    if (!open) return;
    setError('');
    setForm({
      region_code: initial?.region_code ?? '',
      specific_name: initial?.specific_name ?? '',
      full_name: initial?.full_name ?? '',
      parent_code: initial?.parent_code ?? '',
    });
    setLoadingOptions(true);
    fetchRegionOptions()
      .then((data) => setOptions(data.items ?? []))
      .catch(() => setOptions([]))
      .finally(() => setLoadingOptions(false));
  }, [open, initial]);

  if (!open) return null;

  const setField = (key, value) =>
    setForm((prev) => ({ ...prev, [key]: value }));

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    const code = form.region_code.trim();
    const specific = form.specific_name.trim();
    if (!isEdit && !code) {
      setError('지역코드를 입력하세요.');
      return;
    }
    if (!specific) {
      setError('지역명(표시명)을 입력하세요.');
      return;
    }

    const parent = form.parent_code.trim() || null;
    const payload = {
      full_name: form.full_name.trim() || null,
      specific_name: specific,
      parent_code: parent,
    };

    setBusy(true);
    try {
      let saved;
      if (isEdit) {
        saved = await updateRegion(code, payload);
      } else {
        saved = await createRegion({ region_code: code, ...payload });
      }
      onSaved?.(saved);
      onClose();
    } catch (err) {
      setError(
        apiErrorMessage(
          err,
          isEdit ? '수정에 실패했습니다.' : '등록에 실패했습니다.',
        ),
      );
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
        aria-labelledby="region-form-title"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="admin-modal__head">
          <h2 id="region-form-title">
            {isEdit ? '행정구역 수정' : '행정구역 등록'}
          </h2>
          <button type="button" className="admin-modal__close" onClick={onClose}>
            ×
          </button>
        </div>

        <form className="admin-modal__body" onSubmit={handleSubmit}>
          {error && <p className="admin-modal__error">{error}</p>}

          <div className="admin-fld">
            <label htmlFor="region_code">지역코드</label>
            <input
              id="region_code"
              value={form.region_code}
              onChange={(e) => setField('region_code', e.target.value)}
              disabled={isEdit}
              placeholder="예: 1122"
              maxLength={10}
            />
          </div>

          <div className="admin-fld">
            <label htmlFor="specific_name">지역명 (표시명)</label>
            <input
              id="specific_name"
              value={form.specific_name}
              onChange={(e) => setField('specific_name', e.target.value)}
              placeholder="예: 강남구"
              maxLength={20}
            />
          </div>

          <div className="admin-fld">
            <label htmlFor="full_name">전체 명칭 (선택)</label>
            <input
              id="full_name"
              value={form.full_name}
              onChange={(e) => setField('full_name', e.target.value)}
              placeholder="예: 서울특별시 강남구"
              maxLength={100}
            />
          </div>

          <div className="admin-fld">
            <label htmlFor="parent_code">상위 지역</label>
            <select
              id="parent_code"
              value={form.parent_code}
              onChange={(e) => setField('parent_code', e.target.value)}
              disabled={loadingOptions}
            >
              <option value="">(없음 — 시·도)</option>
              {options
                .filter((o) => !isEdit || o.region_code !== form.region_code)
                .map((o) => (
                  <option key={o.region_code} value={o.region_code}>
                    {o.label} ({o.region_code})
                  </option>
                ))}
            </select>
          </div>

          <p className="admin-modal__hint">
            하위 지역·연결 영상이 있으면 삭제할 수 없습니다. 상위 변경 시 순환
            참조는 차단됩니다.
          </p>

          <div className="admin-modal__actions">
            <button
              type="button"
              className="admin-btn"
              onClick={onClose}
              disabled={busy}
            >
              취소
            </button>
            <button
              type="submit"
              className="admin-btn admin-btn--primary"
              disabled={busy}
            >
              {busy ? '저장 중…' : isEdit ? '수정 저장' : '등록'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
