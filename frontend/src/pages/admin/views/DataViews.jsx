/** 데이터 관리 뷰 — 코드·검증·보내기·보존 정책 */
import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import PageHead from '../components/PageHead';
import EmptyState, { StatValue, TableEmptyRow } from '../components/EmptyState';
import {
  ADMIN_ACTION_LABELS,
  deleteRegion,
  clearAllRegions,
  exportRegionsCsv,
  fetchAdminHistory,
  fetchCodeGroups,
  fetchRegionDetail,
  fetchRegions,
  importRegionsCsv,
  fetchRetentionPolicies,
  updateRetentionPolicies,
  runRetentionDryRun,
  runDataIntegrity,
  fetchLastIntegrityRun,
  saveBlobDownload,
  downloadIntegrityReport,
  readApiErrorMessage,
  fetchIntegrityRun,
} from '../../../api/client';
import RegionFormModal from '../components/RegionFormModal';
import CodeGroupEditModal from '../components/CodeGroupEditModal';
import AdminCsvFeedback from '../components/AdminCsvFeedback';
import IntegrityCheckDetailModal from '../components/IntegrityCheckDetailModal';
import RetentionDryRunModal from '../components/RetentionDryRunModal';
import {
  checksToCsvBlob,
  historyItemToIntegrityResult,
  integrityStatusClass,
  integrityStatusLabel,
  integrityTargetLabel,
  INTEGRITY_STATUS_OPTIONS,
  INTEGRITY_TARGET_OPTIONS,
  integrityFixLink,
} from '../integrityConfig';

function regionErrorMessage(err) {
  const status = err?.response?.status;
  if (status === 403) return '관리자 권한이 필요합니다.';
  if (status === 401) return '로그인이 만료되었습니다. 다시 로그인해 주세요.';
  if (!err?.response) return '네트워크 오류로 불러오지 못했습니다.';
  return '행정구역을 불러오지 못했습니다.';
}

function codeGroupErrorMessage(err) {
  const status = err?.response?.status;
  if (status === 403) return '관리자 권한이 필요합니다.';
  if (status === 401) return '로그인이 만료되었습니다.';
  if (!err?.response) return '네트워크 오류로 불러오지 못했습니다.';
  return '코드 그룹을 불러오지 못했습니다.';
}

const REGION_ACTION_LABELS = {
  create: '등록',
  update: '수정',
  delete: '삭제',
  export: 'CSV내보내기',
  import: 'CSV가져오기',
  clear_all: '전체 비우기',
};

function regionHistorySummary(item) {
  const action = item.detail?.action;
  const label = REGION_ACTION_LABELS[action] || ADMIN_ACTION_LABELS[item.action_type] || action;
  const target = item.target_id || '—';
  if (action === 'import') {
    return `${label} · +${item.detail?.created ?? 0} / ~${item.detail?.updated ?? 0}`;
  }
  if (action === 'export') {
    return `${label} · ${item.detail?.row_count ?? 0}행`;
  }
  if (action === 'clear_all') {
    return `${label} · 행정구역 ${item.detail?.region_deleted ?? 0}건`;
  }
  return `${label} · ${target}`;
}

function integrityHistorySummary(item) {
  const d = item.detail || {};
  if (d.action !== 'run') return item.target_id || '—';
  const parts = [
    `이슈 ${d.total_issues ?? 0}건`,
    `정상 ${d.ok_count ?? 0}`,
    `주의 ${d.warn_count ?? 0}`,
    `오류 ${d.error_count ?? 0}`,
  ];
  if (d.delta_issues != null && d.delta_issues !== 0) {
    const sign = d.delta_issues > 0 ? '+' : '';
    parts.push(`이전 대비 ${sign}${d.delta_issues}`);
  }
  return parts.join(' · ');
}

function integrityDeltaClass(delta) {
  if (delta > 0) return 'admin-delta admin-delta--down';
  if (delta < 0) return 'admin-delta admin-delta--up';
  return 'admin-delta';
}

const RETENTION_EXPIRY_LABELS = {
  delete: '삭제',
  archive: '보관',
  anonymize: '익명화',
};

function retentionHistorySummary(item) {
  const changes = item.detail?.changes;
  if (!Array.isArray(changes) || changes.length === 0) {
    return ADMIN_ACTION_LABELS[item.action_type] || '수정';
  }
  const parts = changes.map((c) => {
    const after = c.after || {};
    const before = c.before || {};
    const fields = [];
    if (after.retention_days != null && after.retention_days !== before.retention_days) {
      fields.push(`보존 ${before.retention_days}→${after.retention_days}일`);
    }
    if (after.expiry_action && after.expiry_action !== before.expiry_action) {
      const label = RETENTION_EXPIRY_LABELS[after.expiry_action] || after.expiry_action;
      fields.push(`처리 ${label}`);
    }
    if (after.is_active != null && after.is_active !== before.is_active) {
      fields.push(after.is_active ? '적용' : '중지');
    }
    if (after.notes !== undefined && after.notes !== before.notes) {
      fields.push('메모 변경');
    }
    const summary = fields.length ? fields.join(', ') : '세부 변경';
    return `#${c.id} ${summary}`;
  });
  if (parts.length <= 2) return parts.join(' · ');
  return `${parts.slice(0, 2).join(' · ')} 외 ${parts.length - 2}건`;
}

function retentionPolicyPatches(rows) {
  return rows.map((r) => ({
    id: r.id,
    retention_days: r.retention_days,
    expiry_action: r.expiry_action,
    is_active: r.is_active,
  }));
}

function RegionTreeNode({
  node,
  depth,
  expanded,
  childrenMap,
  loadingParents,
  selectedCode,
  onToggle,
  onActivate,
}) {
  const hasChildren = node.child_count > 0;
  const isExpanded = expanded.has(node.region_code);
  const isLoading = loadingParents.has(node.region_code);
  const children = childrenMap.get(node.region_code) ?? [];
  const levelClass =
    depth === 0 ? 'admin-tnode--l0' : depth === 1 ? 'admin-tnode--l1' : 'admin-tnode--l2';

  return (
    <>
      <div
        className={`admin-tnode ${levelClass} ${
          selectedCode === node.region_code ? 'admin-tnode--active' : ''
        }`}
      >
        <button
          type="button"
          className="admin-tnode__main"
          onClick={() => onActivate(node)}
          aria-expanded={hasChildren ? isExpanded : undefined}
        >
          {hasChildren ? (
            <span
              className="admin-tnode__caret"
              role="presentation"
              onClick={(e) => {
                e.stopPropagation();
                onToggle(node);
              }}
            >
              {isLoading ? '…' : isExpanded ? '▾' : '▸'}
            </span>
          ) : (
            <span className="admin-tnode__caret admin-tnode__caret--spacer" />
          )}
          <span className="admin-tnode__label">
            {node.specific_name || node.full_name || node.region_code}
          </span>
          <span className="admin-tcode">{node.region_code}</span>
        </button>
        {node.child_count > 0 && (
          <span className="admin-tnode__meta">{node.child_count}</span>
        )}
      </div>
      {isExpanded &&
        children.map((child) => (
          <RegionTreeNode
            key={child.region_code}
            node={child}
            depth={depth + 1}
            expanded={expanded}
            childrenMap={childrenMap}
            loadingParents={loadingParents}
            selectedCode={selectedCode}
            onToggle={onToggle}
            onActivate={onActivate}
          />
        ))}
    </>
  );
}

export function DataCodesView() {
  const [roots, setRoots] = useState([]);
  const [rootsTotal, setRootsTotal] = useState(0);
  const [regionLoading, setRegionLoading] = useState(true);
  const [regionError, setRegionError] = useState('');
  const [keyword, setKeyword] = useState('');
  const [searchRows, setSearchRows] = useState([]);
  const [searchTotal, setSearchTotal] = useState(0);
  const [searchPage, setSearchPage] = useState(1);
  const [expanded, setExpanded] = useState(() => new Set());
  const [childrenMap, setChildrenMap] = useState(() => new Map());
  const [loadingParents, setLoadingParents] = useState(() => new Set());
  const [selected, setSelected] = useState(null);

  const [codeGroups, setCodeGroups] = useState([]);
  const [groupsLoading, setGroupsLoading] = useState(true);
  const [groupsError, setGroupsError] = useState('');

  const [modalOpen, setModalOpen] = useState(false);
  const [modalMode, setModalMode] = useState('create');
  const [modalInitial, setModalInitial] = useState(null);
  const [deleteBusy, setDeleteBusy] = useState(false);
  const [actionError, setActionError] = useState('');
  const [csvFeedback, setCsvFeedback] = useState(null);
  const [csvBusy, setCsvBusy] = useState(false);
  const [csvBusyMode, setCsvBusyMode] = useState(null);
  const [clearBusy, setClearBusy] = useState(false);
  const [exportFormat, setExportFormat] = useState('region');
  const [regionHistory, setRegionHistory] = useState([]);
  const [codeEditItem, setCodeEditItem] = useState(null);

  const isSearchMode = keyword.trim().length > 0;

  const loadRoots = useCallback(async () => {
    setRegionLoading(true);
    setRegionError('');
    try {
      const data = await fetchRegions({ page: 1, per_page: 100 });
      setRoots(data.items);
      setRootsTotal(data.total);
    } catch (err) {
      setRegionError(regionErrorMessage(err));
      setRoots([]);
      setRootsTotal(0);
    } finally {
      setRegionLoading(false);
    }
  }, []);

  const loadSearch = useCallback(async () => {
    const q = keyword.trim();
    if (!q) return;
    setRegionLoading(true);
    setRegionError('');
    try {
      const data = await fetchRegions({ q, page: searchPage, per_page: 30 });
      setSearchRows(data.items);
      setSearchTotal(data.total);
    } catch (err) {
      setRegionError(regionErrorMessage(err));
      setSearchRows([]);
      setSearchTotal(0);
    } finally {
      setRegionLoading(false);
    }
  }, [keyword, searchPage]);

  const loadCodeGroups = useCallback(async () => {
    setGroupsLoading(true);
    setGroupsError('');
    try {
      const data = await fetchCodeGroups();
      setCodeGroups(data.groups ?? []);
    } catch (err) {
      setGroupsError(codeGroupErrorMessage(err));
      setCodeGroups([]);
    } finally {
      setGroupsLoading(false);
    }
  }, []);

  const loadRegionHistory = useCallback(async () => {
    try {
      const data = await fetchAdminHistory({
        target_type: 'region',
        per_page: 8,
      });
      setRegionHistory(data.items ?? []);
    } catch {
      setRegionHistory([]);
    }
  }, []);

  useEffect(() => {
    loadRoots();
    loadCodeGroups();
    loadRegionHistory();
  }, [loadRoots, loadCodeGroups, loadRegionHistory]);

  useEffect(() => {
    if (!isSearchMode) return;
    loadSearch();
  }, [isSearchMode, loadSearch]);

  const loadChildren = async (parentCode) => {
    setLoadingParents((prev) => new Set(prev).add(parentCode));
    try {
      const data = await fetchRegions({ parent_code: parentCode, per_page: 200 });
      setChildrenMap((prev) => new Map(prev).set(parentCode, data.items));
    } catch (err) {
      setRegionError(regionErrorMessage(err));
    } finally {
      setLoadingParents((prev) => {
        const next = new Set(prev);
        next.delete(parentCode);
        return next;
      });
    }
  };

  const handleToggle = async (node) => {
    const code = node.region_code;
    if (expanded.has(code)) {
      setExpanded((prev) => {
        const next = new Set(prev);
        next.delete(code);
        return next;
      });
      return;
    }
    if (!childrenMap.has(code)) {
      await loadChildren(code);
    }
    setExpanded((prev) => new Set(prev).add(code));
  };

  const handleActivate = async (node) => {
    void handleSelect(node);
    if (node.child_count > 0 && !expanded.has(node.region_code)) {
      await handleToggle(node);
    }
  };

  const handleSelect = async (node) => {
    setSelected(node);
    setActionError('');
    try {
      const detail = await fetchRegionDetail(node.region_code);
      setSelected(detail);
    } catch {
      /* 목록 데이터로도 상세 표시 가능 */
    }
  };

  const resetRegionTreeView = useCallback(() => {
    setExpanded(new Set());
    setChildrenMap(new Map());
    setLoadingParents(new Set());
    setSelected(null);
    setActionError('');
  }, []);

  const handleRegionListRefresh = useCallback(async () => {
    resetRegionTreeView();
    await loadRoots();
  }, [resetRegionTreeView, loadRoots]);

  const reloadExpandedChildren = useCallback(async (expandedSet) => {
    const entries = await Promise.all(
      [...expandedSet].map(async (code) => {
        try {
          const data = await fetchRegions({ parent_code: code, per_page: 200 });
          return [code, data.items];
        } catch {
          return [code, []];
        }
      }),
    );
    setChildrenMap(new Map(entries));
  }, []);

  const refreshRegions = useCallback(async () => {
    if (isSearchMode) {
      await loadSearch();
      return;
    }
    await loadRoots();
    if (expanded.size > 0) {
      await reloadExpandedChildren(expanded);
    }
    if (selected?.region_code) {
      try {
        const detail = await fetchRegionDetail(selected.region_code);
        setSelected(detail);
      } catch {
        setSelected(null);
      }
    }
  }, [
    isSearchMode,
    loadSearch,
    loadRoots,
    expanded,
    reloadExpandedChildren,
    selected?.region_code,
  ]);

  const openCreateModal = (parentCode = '') => {
    setModalMode('create');
    setModalInitial({
      parent_code: parentCode || selected?.region_code || '',
    });
    setModalOpen(true);
  };

  const openEditModal = () => {
    if (!selected) return;
    setModalMode('edit');
    setModalInitial(selected);
    setModalOpen(true);
  };

  const handleDelete = async () => {
    if (!selected) return;
    const { region_code, child_count, video_count, specific_name, full_name } =
      selected;
    if (child_count > 0 || video_count > 0) {
      setActionError('하위 지역 또는 연결 영상이 있으면 삭제할 수 없습니다.');
      return;
    }
    const label = specific_name || full_name || region_code;
    if (!window.confirm(`「${label}」(${region_code}) 행정구역을 삭제할까요?`)) {
      return;
    }
    setDeleteBusy(true);
    setActionError('');
    try {
      await deleteRegion(region_code);
      setSelected(null);
      setExpanded((prev) => {
        const next = new Set(prev);
        next.delete(region_code);
        return next;
      });
      await refreshRegions();
      await loadRegionHistory();
    } catch (err) {
      const detail = err?.response?.data?.detail;
      setActionError(
        typeof detail === 'string' ? detail : '삭제에 실패했습니다.',
      );
    } finally {
      setDeleteBusy(false);
    }
  };

  const handleSaved = async (saved) => {
    setSelected(saved);
    if (saved.parent_code) {
      setExpanded((prev) => new Set(prev).add(saved.parent_code));
    }
    setChildrenMap(new Map());
    await refreshRegions();
    await loadRegionHistory();
  };

  const handleClearAllRegions = async () => {
    if (
      !window.confirm(
        '행정구역(region)과 법정동 매핑(region_legal_dong)을 모두 삭제합니다.\n' +
          '연결된 영상의 지역 코드는 해제됩니다.\n\n계속할까요?',
      )
    ) {
      return;
    }
    setClearBusy(true);
    setCsvFeedback(null);
    try {
      const result = await clearAllRegions();
      setChildrenMap(new Map());
      setExpanded(new Set());
      setSelected(null);
      await refreshRegions();
      await loadRegionHistory();
      setCsvFeedback({
        type: 'success',
        text:
          `전체 비우기 완료 — 행정구역 ${result.region_deleted}건, ` +
          `법정동 매핑 ${result.legal_dong_deleted}건` +
          (result.video_unlinked
            ? `, 영상 연결 해제 ${result.video_unlinked}건`
            : ''),
      });
    } catch (err) {
      const detail = err.response?.data?.detail;
      setCsvFeedback({
        type: 'error',
        text:
          typeof detail === 'string' ? detail : '전체 비우기에 실패했습니다.',
      });
    } finally {
      setClearBusy(false);
    }
  };

  const handleExportCsv = async () => {
    setCsvBusy(true);
    setCsvBusyMode('export');
    setCsvFeedback(null);
    try {
      const blob = await exportRegionsCsv(exportFormat);
      const filename =
        exportFormat === 'administrative_dong'
          ? 'administrative_dong.csv'
          : 'regions.csv';
      saveBlobDownload(blob, filename);
      setCsvFeedback({
        type: 'success',
        text: `CSV보내기를 완료했습니다. (${filename})`,
      });
      await loadRegionHistory();
    } catch (err) {
      const message = await readApiErrorMessage(
        err,
        'CSV보내기에 실패했습니다. 로그인 상태와 네트워크를 확인해 주세요.',
      );
      setCsvFeedback({ type: 'error', text: message });
    } finally {
      setCsvBusy(false);
      setCsvBusyMode(null);
    }
  };

  const handleImportCsv = async (e) => {
    const file = e.target.files?.[0];
    e.target.value = '';
    if (!file) return;
    setCsvBusy(true);
    setCsvBusyMode('import');
    setCsvFeedback(null);
    try {
      const preview = await importRegionsCsv(file, true);
      if (preview.errors?.length) {
        setCsvFeedback({ type: 'error', text: preview.errors.join(' ') });
        return;
      }
      const isAdminDong = preview.format === 'administrative_dong';
      const msg = isAdminDong
        ? `행정동 CSV (${preview.csv_rows?.toLocaleString?.() ?? preview.csv_rows ?? 0}행)\n` +
          `지역 — 신규 ${preview.created}건, 수정 ${preview.updated}건\n` +
          `법정동 매핑 — 신규 ${preview.legal_dong_created}건, 수정 ${preview.legal_dong_updated}건\n` +
          '가져오기를 진행할까요?'
        : `가져오기 예정: 신규 ${preview.created}건, 수정 ${preview.updated}건. 진행할까요?`;
      if (!window.confirm(msg)) return;
      const result = await importRegionsCsv(file, false);
      if (result.errors?.length) {
        setCsvFeedback({ type: 'error', text: result.errors.join(' ') });
        return;
      }
      setChildrenMap(new Map());
      await refreshRegions();
      await loadRegionHistory();
      setCsvFeedback({
        type: 'success',
        text: `CSV가져오기를 완료했습니다. 신규 ${result.created}건, 수정 ${result.updated}건, 건너뜀 ${result.skipped}건`,
      });
    } catch (err) {
      const data = err.response?.data;
      if (data?.errors?.length) {
        setCsvFeedback({ type: 'error', text: data.errors.join(' ') });
      } else if (typeof data?.detail === 'string') {
        setCsvFeedback({ type: 'error', text: data.detail });
      } else {
        setCsvFeedback({
          type: 'error',
          text: 'CSV가져오기에 실패했습니다. 파일 형식과 로그인 상태를 확인해 주세요.',
        });
      }
    } finally {
      setCsvBusy(false);
      setCsvBusyMode(null);
    }
  };

  const flatCodeRows = useMemo(() => {
    const rows = [];
    for (const group of codeGroups) {
      for (const item of group.items ?? []) {
        rows.push({
          groupKey: group.group,
          groupLabel: group.group_label,
          code: item.code,
          label: item.label,
          ref: item.ref_count,
          description: item.description,
          is_active: item.is_active !== false,
        });
      }
    }
    return rows;
  }, [codeGroups]);

  const searchPages = Math.max(1, Math.ceil(searchTotal / 30));

  return (
    <>
      <PageHead
        viewId="data-codes"
        desc="지역(행정구역)·역할·검색유형 등 시스템 기준 코드를 관리합니다. 왼쪽은 CCTV·검색이 참조하는 행정구역 계층, 오른쪽은 앱 전역 enum 코드입니다."
      />

      {csvBusy && csvBusyMode === 'import' && (
        <div className="admin-csv-busy-banner admin-mb" role="status" aria-live="polite">
          CSV를 분석·적재하는 중입니다. 대용량 파일은 수십 초 걸릴 수 있습니다.
        </div>
      )}
      {csvBusy && csvBusyMode === 'export' && (
        <div className="admin-csv-busy-banner admin-mb" role="status" aria-live="polite">
          CSV 파일을 생성하는 중입니다.
        </div>
      )}
      {clearBusy && (
        <div className="admin-csv-busy-banner admin-mb" role="status" aria-live="polite">
          행정구역 데이터를 비우는 중입니다.
        </div>
      )}

      <div className="admin-toolbar admin-mb">
        <input
          type="search"
          placeholder="코드·지역명 검색"
          value={keyword}
          onChange={(e) => {
            setKeyword(e.target.value);
            setSearchPage(1);
          }}
        />
        <button
          type="button"
          className="admin-btn"
          onClick={() => {
            setKeyword('');
            setSearchPage(1);
            resetRegionTreeView();
            loadRoots();
          }}
          disabled={
            !keyword && !regionError && expanded.size === 0 && !selected
          }
        >
          초기화
        </button>
        <div className="admin-spacer" />
        <select
          className="admin-toolbar-select"
          value={exportFormat}
          onChange={(e) => setExportFormat(e.target.value)}
          disabled={csvBusy || clearBusy}
          aria-label="CSV내보내기 형식"
        >
          <option value="region">계층 (region)</option>
          <option value="administrative_dong">행정동 원본</option>
        </select>
        <button
          type="button"
          className="admin-btn"
          onClick={handleExportCsv}
          disabled={csvBusy || clearBusy}
        >
          CSV내보내기
        </button>
        <label className="admin-btn admin-btn--file">
          CSV가져오기
          <input
            type="file"
            accept=".csv,text/csv"
            onChange={handleImportCsv}
            disabled={csvBusy || clearBusy}
            hidden
          />
        </label>
        <button
          type="button"
          className="admin-btn admin-btn--danger"
          onClick={handleClearAllRegions}
          disabled={csvBusy || clearBusy || regionLoading}
        >
          전체 비우기
        </button>
        <button
          type="button"
          className="admin-btn admin-btn--primary"
          onClick={() => openCreateModal()}
          disabled={clearBusy}
        >
          코드 추가
        </button>
      </div>

      <AdminCsvFeedback feedback={csvFeedback} />

      <RegionFormModal
        open={modalOpen}
        mode={modalMode}
        initial={modalInitial}
        onClose={() => setModalOpen(false)}
        onSaved={handleSaved}
      />

      <CodeGroupEditModal
        open={!!codeEditItem}
        item={codeEditItem}
        onClose={() => setCodeEditItem(null)}
        onSaved={() => loadCodeGroups()}
      />

      <div className="admin-cols">
        <div className="admin-card">
          <div className="admin-card-h">
            <div>
              행정구역 (region)
              <span className="admin-card-hint">영상·CCTV 폴더가 참조하는 계층</span>
            </div>
            {!isSearchMode && roots.length > 0 && (
              <button
                type="button"
                className="admin-btn admin-btn--sm"
                onClick={handleRegionListRefresh}
                disabled={regionLoading || csvBusy || clearBusy}
              >
                목록 새로고침
              </button>
            )}
          </div>
          <div className="admin-card-b">
            {regionLoading && (
              <p className="admin-inline-status">행정구역 불러오는 중…</p>
            )}

            {!regionLoading && regionError && (
              <div className="admin-inline-error">
                <p>{regionError}</p>
                <button
                  type="button"
                  className="admin-btn admin-btn--sm"
                  onClick={isSearchMode ? loadSearch : loadRoots}
                >
                  다시 시도
                </button>
              </div>
            )}

            {!regionLoading && !regionError && isSearchMode && searchRows.length === 0 && (
              <EmptyState message={`「${keyword.trim()}」에 맞는 행정구역이 없습니다.`} />
            )}

            {!regionLoading && !regionError && !isSearchMode && roots.length === 0 && (
              <div className="admin-empty admin-empty--cta">
                <p>등록된 행정구역이 없습니다.</p>
                <p className="admin-empty__sub">
                  서버 기동 시 기본 시·도 데이터가 자동 시드됩니다. 백엔드를 재시작해
                  보세요.
                </p>
                <button
                  type="button"
                  className="admin-btn admin-btn--primary admin-btn--sm"
                  onClick={handleRegionListRefresh}
                >
                  목록 새로고침
                </button>
              </div>
            )}

            {!regionLoading && !regionError && isSearchMode && searchRows.length > 0 && (
              <div className="admin-tree">
                {searchRows.map((row) => (
                  <div
                    key={row.region_code}
                    className={`admin-tnode admin-tnode--l0 ${
                      selected?.region_code === row.region_code
                        ? 'admin-tnode--active'
                        : ''
                    }`}
                  >
                    <button
                      type="button"
                      className="admin-tnode__main"
                      onClick={() => handleSelect(row)}
                    >
                      <span className="admin-tnode__label">
                        {row.full_name || row.specific_name}
                      </span>
                      <span className="admin-tcode">{row.region_code}</span>
                    </button>
                  </div>
                ))}
                {searchTotal > 30 && (
                  <div className="admin-pager">
                    <button
                      type="button"
                      className="admin-btn admin-btn--sm"
                      disabled={searchPage <= 1}
                      onClick={() => setSearchPage((p) => p - 1)}
                    >
                      이전
                    </button>
                    <span>
                      {searchPage} / {searchPages} ({searchTotal}건)
                    </span>
                    <button
                      type="button"
                      className="admin-btn admin-btn--sm"
                      disabled={searchPage >= searchPages}
                      onClick={() => setSearchPage((p) => p + 1)}
                    >
                      다음
                    </button>
                  </div>
                )}
              </div>
            )}

            {!regionLoading && !regionError && !isSearchMode && roots.length > 0 && (
              <div className="admin-tree">
                {roots.map((node) => (
                  <RegionTreeNode
                    key={node.region_code}
                    node={node}
                    depth={0}
                    expanded={expanded}
                    childrenMap={childrenMap}
                    loadingParents={loadingParents}
                    selectedCode={selected?.region_code}
                    onToggle={handleToggle}
                    onActivate={handleActivate}
                  />
                ))}
                {rootsTotal > roots.length && (
                  <p className="admin-footnote">상위 {roots.length} / {rootsTotal}건 표시</p>
                )}
              </div>
            )}

            {selected && (
              <div className="admin-region-detail">
                <div className="admin-region-detail__head">
                  <div className="admin-region-detail__title">선택 항목</div>
                  <div className="admin-region-detail__actions">
                    <button
                      type="button"
                      className="admin-btn admin-btn--sm"
                      onClick={() => openCreateModal(selected.region_code)}
                    >
                      하위 추가
                    </button>
                    <button
                      type="button"
                      className="admin-btn admin-btn--sm"
                      onClick={openEditModal}
                    >
                      수정
                    </button>
                    <button
                      type="button"
                      className="admin-btn admin-btn--sm admin-btn--danger"
                      onClick={handleDelete}
                      disabled={
                        deleteBusy ||
                        (selected.child_count ?? 0) > 0 ||
                        (selected.video_count ?? 0) > 0
                      }
                      title={
                        (selected.child_count ?? 0) > 0 ||
                        (selected.video_count ?? 0) > 0
                          ? '하위 지역·연결 영상이 있으면 삭제 불가'
                          : undefined
                      }
                    >
                      {deleteBusy ? '삭제 중…' : '삭제'}
                    </button>
                  </div>
                </div>
                {actionError && (
                  <p className="admin-modal__error admin-modal__error--inline">
                    {actionError}
                  </p>
                )}
                <dl>
                  <div>
                    <dt>코드</dt>
                    <dd>{selected.region_code}</dd>
                  </div>
                  <div>
                    <dt>전체 명칭</dt>
                    <dd>{selected.full_name || '—'}</dd>
                  </div>
                  <div>
                    <dt>하위 지역</dt>
                    <dd>{selected.child_count ?? 0}건</dd>
                  </div>
                  <div>
                    <dt>연결 영상</dt>
                    <dd>{selected.video_count ?? 0}건</dd>
                  </div>
                </dl>
              </div>
            )}

            <p className="admin-footnote">
              parent_code 기반 계층(self-FK). 항목을 클릭하면 하위 지역이 펼쳐지고, ▸ 아이콘으로 접을 수 있습니다. 목록 새로고침 시 시·도만 보이는 초기 상태로 돌아갑니다.
            </p>

            {regionHistory.length > 0 && (
              <div className="admin-change-log">
                <div className="admin-change-log__title">최근 변경 이력</div>
                <ul>
                  {regionHistory.map((item) => (
                    <li key={item.id}>
                      <span className="admin-change-log__time">
                        {new Date(item.created_at).toLocaleString('ko-KR')}
                      </span>
                      <span>{item.actor_name || '—'}</span>
                      <span>{regionHistorySummary(item)}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>

        <div className="admin-card">
          <div className="admin-card-h">
            코드 그룹
            <span className="admin-card-hint">앱 전역 enum · DB에 저장된 참조 수</span>
          </div>
          <div
            className="admin-card-b admin-table-wrap"
            style={{ paddingTop: 6 }}
          >
            {groupsLoading && (
              <p className="admin-inline-status" style={{ padding: '12px 14px' }}>
                코드 그룹 불러오는 중…
              </p>
            )}

            {!groupsLoading && groupsError && (
              <div className="admin-inline-error" style={{ padding: '12px 14px' }}>
                <p>{groupsError}</p>
                <button
                  type="button"
                  className="admin-btn admin-btn--sm"
                  onClick={loadCodeGroups}
                >
                  다시 시도
                </button>
              </div>
            )}

            {!groupsLoading && !groupsError && (
              <table>
                <thead>
                  <tr>
                    <th>그룹</th>
                    <th>코드값</th>
                    <th>라벨</th>
                    <th>상태</th>
                    <th style={{ textAlign: 'right' }}>참조</th>
                    <th style={{ textAlign: 'right' }} />
                  </tr>
                </thead>
                <tbody>
                  {flatCodeRows.length === 0 ? (
                    <TableEmptyRow colSpan={6} message="등록된 코드 그룹이 없습니다." />
                  ) : (
                    flatCodeRows.map((row, idx) => (
                      <tr
                        key={`${row.groupKey}-${row.code}-${idx}`}
                        className={!row.is_active ? 'admin-row--muted' : undefined}
                      >
                        <td>{row.groupLabel}</td>
                        <td>
                          <code>{row.code}</code>
                        </td>
                        <td>{row.label}</td>
                        <td>
                          {row.is_active ? (
                            <span className="admin-pill admin-pill--ok">활성</span>
                          ) : (
                            <span className="admin-pill admin-pill--muted">비활성</span>
                          )}
                        </td>
                        <td style={{ textAlign: 'right' }}>{row.ref}</td>
                        <td style={{ textAlign: 'right' }}>
                          <button
                            type="button"
                            className="admin-btn admin-btn--sm"
                            onClick={() => setCodeEditItem(row)}
                          >
                            수정
                          </button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            )}
          </div>
        </div>
      </div>
    </>
  );
}

export function DataValidateView() {
  const [loading, setLoading] = useState(false);
  const [initialLoading, setInitialLoading] = useState(true);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [result, setResult] = useState(null);
  const [activeRunId, setActiveRunId] = useState(null);
  const [reportBusy, setReportBusy] = useState(false);
  const [targetFilter, setTargetFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [history, setHistory] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [detailCheck, setDetailCheck] = useState(null);

  const loadHistory = useCallback(async () => {
    try {
      const data = await fetchAdminHistory({
        target_type: 'integrity_check',
        per_page: 10,
      });
      setHistory(data.items ?? []);
    } catch {
      setHistory([]);
    }
  }, []);

  const loadLastRun = useCallback(async () => {
    try {
      const data = await fetchLastIntegrityRun();
      setResult(data);
      setActiveRunId(data.run_id ?? null);
    } catch (err) {
      if (err?.response?.status !== 404) {
        setError('최근 검사 결과를 불러오지 못했습니다.');
      }
    }
  }, []);

  useEffect(() => {
    let active = true;
    (async () => {
      setInitialLoading(true);
      await Promise.all([loadLastRun(), loadHistory()]);
      if (active) setInitialLoading(false);
    })();
    return () => {
      active = false;
    };
  }, [loadLastRun, loadHistory]);

  const summary = useMemo(() => {
    if (!result?.checks?.length) return null;
    const checks = result.checks;
    return {
      ok: checks.filter((c) => c.status === 'ok').length,
      warn: checks.filter((c) => c.status === 'warn').length,
      error: checks.filter((c) => c.status === 'error').length,
      totalIssues: result.total_issues ?? 0,
    };
  }, [result]);

  const displayedChecks = useMemo(() => {
    if (!result?.checks) return [];
    return result.checks.filter((c) => {
      if (targetFilter && c.target !== targetFilter) return false;
      if (statusFilter === 'issues' && c.status === 'ok') return false;
      if (statusFilter === 'error' && c.status !== 'error') return false;
      if (statusFilter === 'warn' && c.status !== 'warn') return false;
      return true;
    });
  }, [result, targetFilter, statusFilter]);

  const runCheck = async () => {
    setLoading(true);
    setError('');
    setMessage('');
    try {
      const data = await runDataIntegrity();
      setResult(data);
      setActiveRunId(data.run_id ?? null);
      setMessage(
        data.total_issues > 0
          ? `정합성 검사를 완료했습니다. 이슈 ${data.total_issues}건이 발견되었습니다.`
          : '정합성 검사를 완료했습니다. 이슈가 없습니다.',
      );
      await loadHistory();
    } catch (err) {
      setError(
        err?.response?.status === 403
          ? '관리자 권한이 필요합니다.'
          : '정합성 검사를 실행하지 못했습니다.',
      );
    } finally {
      setLoading(false);
    }
  };

  const restoreHistoryRun = async (item) => {
    setHistoryLoading(true);
    setError('');
    setMessage('');
    try {
      let restored = historyItemToIntegrityResult(item);
      if (!restored) {
        restored = await fetchIntegrityRun(item.id);
      }
      setResult(restored);
      setActiveRunId(item.id);
      setMessage(
        `${new Date(item.created_at).toLocaleString('ko-KR')} 검사 결과를 불러왔습니다.`,
      );
    } catch {
      setError('과거 검사 결과를 불러오지 못했습니다.');
    } finally {
      setHistoryLoading(false);
    }
  };

  const downloadCurrentResult = () => {
    if (!result?.checks?.length) {
      setError('보낼 검사 결과가 없습니다.');
      return;
    }
    const blob = checksToCsvBlob(result.checks);
    saveBlobDownload(blob, 'integrity_report.csv');
    setMessage('현재 표시 중인 검사 결과 CSV를 저장했습니다.');
  };

  const downloadFreshReport = async () => {
    setReportBusy(true);
    setError('');
    try {
      const blob = await downloadIntegrityReport('fresh');
      saveBlobDownload(blob, 'integrity_report_fresh.csv');
      setMessage('새로 검사한 결과 CSV를 저장했습니다.');
    } catch {
      setError('새 검사 리포트보내기에 실패했습니다.');
    } finally {
      setReportBusy(false);
    }
  };

  return (
    <>
      <PageHead
        viewId="data-validate"
        desc="테이블 간 참조 무결성과 데이터 정합성을 검사합니다. 실행 이력은 감사 로그에 기록됩니다."
      />
      <div className="admin-toolbar">
        <button
          type="button"
          className="admin-btn admin-btn--primary"
          onClick={runCheck}
          disabled={loading || initialLoading}
        >
          {loading ? '검사 중…' : '정합성 검사 실행'}
        </button>
        <span className="admin-pill admin-pill--muted">
          마지막 검사{' '}
          {result?.ran_at
            ? new Date(result.ran_at).toLocaleString('ko-KR')
            : '—'}
        </span>
        {result && (
          <span
            className={
              result.total_issues > 0
                ? 'admin-pill admin-pill--err'
                : 'admin-pill admin-pill--ok'
            }
          >
            이슈 {result.total_issues}건
          </span>
        )}
        <div className="admin-spacer" />
        <select
          className="admin-toolbar-select"
          value={targetFilter}
          onChange={(e) => setTargetFilter(e.target.value)}
          disabled={!result}
          aria-label="대상 필터"
        >
          {INTEGRITY_TARGET_OPTIONS.map((opt) => (
            <option key={opt.value || 'all'} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
        <select
          className="admin-toolbar-select"
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          disabled={!result}
          aria-label="심각도 필터"
        >
          {INTEGRITY_STATUS_OPTIONS.map((opt) => (
            <option key={opt.value || 'all'} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
        <button
          type="button"
          className="admin-btn"
          onClick={downloadCurrentResult}
          disabled={!result?.checks?.length}
        >
          결과 CSV
        </button>
        <button
          type="button"
          className="admin-btn"
          onClick={downloadFreshReport}
          disabled={reportBusy || loading}
        >
          {reportBusy ? '검사·저장 중…' : '새 검사 후 CSV'}
        </button>
      </div>

      {message && <p className="admin-inline-ok admin-mb">{message}</p>}

      {error && (
        <div className="admin-inline-error admin-mb">
          <p>{error}</p>
          <button type="button" className="admin-btn admin-btn--sm" onClick={runCheck}>
            다시 시도
          </button>
        </div>
      )}

      {summary && (
        <div className="admin-stat-grid admin-mb">
          <div className="admin-stat admin-stat--green">
            <div className="admin-label">정상 항목</div>
            <StatValue value={summary.ok} unit="개" />
          </div>
          <div className="admin-stat admin-stat--amber">
            <div className="admin-label">주의 항목</div>
            <StatValue value={summary.warn} unit="개" />
          </div>
          <div className="admin-stat admin-stat--red">
            <div className="admin-label">오류 항목</div>
            <StatValue value={summary.error} unit="개" />
          </div>
          <div className="admin-stat">
            <div className="admin-label">총 이슈</div>
            <StatValue value={summary.totalIssues} unit="건" />
            {result?.delta_issues != null && result.delta_issues !== 0 && (
              <div className={integrityDeltaClass(result.delta_issues)}>
                이전 대비 {result.delta_issues > 0 ? '+' : ''}
                {result.delta_issues}
              </div>
            )}
          </div>
        </div>
      )}

      <div className="admin-card admin-table-wrap">
        <table>
          <thead>
            <tr>
              <th>검사 항목</th>
              <th>대상</th>
              <th>검사 내용</th>
              <th>결과</th>
              <th>이슈</th>
              <th>샘플</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {!result ? (
              <TableEmptyRow
                colSpan={7}
                message={
                  initialLoading
                    ? '최근 검사 결과를 불러오는 중…'
                    : '정합성 검사를 실행하면 결과가 표시됩니다.'
                }
              />
            ) : displayedChecks.length === 0 ? (
              <TableEmptyRow
                colSpan={7}
                message="필터 조건에 맞는 검사 항목이 없습니다."
              />
            ) : (
              displayedChecks.map((row) => {
                const fixLink = integrityFixLink(row);
                return (
                  <tr
                    key={row.check_id}
                    className="admin-row--clickable"
                    onClick={() => setDetailCheck(row)}
                  >
                    <td>{row.label}</td>
                    <td>{integrityTargetLabel(row.target)}</td>
                    <td>{row.description}</td>
                    <td>
                      <span className={integrityStatusClass(row.status)}>
                        {integrityStatusLabel(row.status)}
                      </span>
                    </td>
                    <td style={{ textAlign: 'right' }}>{row.issue_count}</td>
                    <td className="admin-table-samples">
                      {row.samples?.length ? row.samples.join(', ') : '—'}
                    </td>
                    <td style={{ textAlign: 'right' }}>
                      {fixLink ? (
                        <Link
                          to={`/admin/${fixLink.viewId}`}
                          className="admin-table-link"
                          onClick={(e) => e.stopPropagation()}
                        >
                          {fixLink.label}
                        </Link>
                      ) : (
                        '—'
                      )}
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
        {result && (
          <p className="admin-footnote">
            행을 클릭하면 이슈 전체 목록·복사·CSV 다운로드를 할 수 있습니다.
          </p>
        )}
      </div>

      <div className="admin-card admin-table-wrap">
        <div className="admin-card-h">최근 검사 이력 (감사 로그)</div>
        <table>
          <thead>
            <tr>
              <th>일시</th>
              <th>요약</th>
              <th>실행자</th>
            </tr>
          </thead>
          <tbody>
            {history.length === 0 ? (
              <TableEmptyRow colSpan={3} message="검사 이력이 없습니다." />
            ) : (
              history.map((item) => (
                <tr
                  key={item.id}
                  className={`admin-history-row${
                    activeRunId === item.id ? ' admin-history-row--active' : ''
                  }`}
                  onClick={() => restoreHistoryRun(item)}
                >
                  <td>{new Date(item.created_at).toLocaleString('ko-KR')}</td>
                  <td>
                    {integrityHistorySummary(item)}
                    {historyLoading && activeRunId === item.id ? ' …' : ''}
                  </td>
                  <td>{item.actor_name || '—'}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
        <p className="admin-footnote">
          이력 행을 클릭하면 해당 시점의 검사 결과를 다시 불러옵니다.
        </p>
      </div>

      <IntegrityCheckDetailModal
        open={!!detailCheck}
        check={detailCheck}
        onClose={() => setDetailCheck(null)}
      />
    </>
  );
}

export function DataRetentionView() {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [saving, setSaving] = useState(false);
  const [history, setHistory] = useState([]);
  const [dryRunOpen, setDryRunOpen] = useState(false);
  const [dryRunItems, setDryRunItems] = useState([]);
  const [dryRunTitle, setDryRunTitle] = useState('');
  const [dryRunLoading, setDryRunLoading] = useState(false);
  const [dryRunError, setDryRunError] = useState('');

  const loadHistory = useCallback(async () => {
    try {
      const data = await fetchAdminHistory({
        target_type: 'retention_policy',
        per_page: 10,
      });
      setHistory(data.items ?? []);
    } catch {
      setHistory([]);
    }
  }, []);

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const data = await fetchRetentionPolicies();
      setRows(data.items ?? []);
      await loadHistory();
    } catch {
      setError('보존 정책을 불러오지 못했습니다.');
      setRows([]);
    } finally {
      setLoading(false);
    }
  }, [loadHistory]);

  useEffect(() => {
    load();
  }, [load]);

  const patchRow = (id, field, value) => {
    setRows((prev) =>
      prev.map((r) => (r.id === id ? { ...r, [field]: value } : r)),
    );
  };

  const handleSave = async () => {
    setSaving(true);
    setError('');
    setMessage('');
    try {
      const data = await updateRetentionPolicies(
        rows.map((r) => ({
          id: r.id,
          retention_days: r.retention_days,
          expiry_action: r.expiry_action,
          is_active: r.is_active,
          notes: r.notes,
        })),
      );
      setRows(data.items ?? []);
      setMessage('보존 정책을 저장했습니다.');
      await loadHistory();
    } catch {
      setError('정책 저장에 실패했습니다.');
    } finally {
      setSaving(false);
    }
  };

  const openDryRun = async (policyId = null, title = '보존 정책 드라이런') => {
    setDryRunOpen(true);
    setDryRunTitle(title);
    setDryRunItems([]);
    setDryRunError('');
    setDryRunLoading(true);
    try {
      const data = await runRetentionDryRun({
        policyId,
        policies: retentionPolicyPatches(rows),
      });
      setDryRunItems(data.items ?? []);
    } catch {
      setDryRunError('드라이런 미리보기에 실패했습니다.');
    } finally {
      setDryRunLoading(false);
    }
  };

  const expiryLabel = (v) => RETENTION_EXPIRY_LABELS[v] || v;
  const totalExpired = useMemo(
    () => rows.reduce((sum, row) => sum + (row.expired_count ?? 0), 0),
    [rows],
  );

  return (
    <>
      <PageHead
        viewId="data-retention"
        desc="데이터 유형별 보존 기간과 자동 삭제 정책을 설정합니다. 영상·임베딩 등 민감·대용량 데이터의 만료 관리가 핵심입니다."
      />
      <div className="admin-toolbar admin-mb">
        <button
          type="button"
          className="admin-btn admin-btn--primary"
          onClick={handleSave}
          disabled={saving || loading || rows.length === 0}
        >
          {saving ? '저장 중…' : '정책 저장'}
        </button>
        <button type="button" className="admin-btn" onClick={load} disabled={loading}>
          새로고침
        </button>
        <button
          type="button"
          className="admin-btn"
          onClick={() => openDryRun(null, '전체 보존 정책 드라이런')}
          disabled={loading || rows.length === 0}
        >
          전체 드라이런
        </button>
        {message && <span className="admin-inline-ok">{message}</span>}
        {!loading && totalExpired > 0 && (
          <span className="admin-warn-tag">
            만료 예정 {totalExpired.toLocaleString()}건
          </span>
        )}
      </div>

      {error && (
        <div className="admin-inline-error admin-mb">
          <p>{error}</p>
          <button type="button" className="admin-btn admin-btn--sm" onClick={load}>
            다시 시도
          </button>
        </div>
      )}

      <div className="admin-card admin-table-wrap">
        <div className="admin-card-h">보존 정책</div>
        <table>
          <thead>
            <tr>
              <th>데이터 유형</th>
              <th>테이블/저장소</th>
              <th>보존 기간</th>
              <th>만료 처리</th>
              <th style={{ textAlign: 'right' }}>현재 보관량</th>
              <th style={{ textAlign: 'right' }}>만료 예정</th>
              <th>상태</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <TableEmptyRow colSpan={8} message="불러오는 중…" />
            ) : rows.length === 0 ? (
              <TableEmptyRow colSpan={8} message="보존 정책이 없습니다." />
            ) : (
              rows.map((row) => (
                <tr key={row.id} className={!row.is_active ? 'admin-row--muted' : undefined}>
                  <td>
                    <strong>{row.data_label}</strong>
                    {row.notes && (
                      <div className="admin-cell-sub">{row.notes}</div>
                    )}
                  </td>
                  <td>{row.storage_target}</td>
                  <td>
                    <input
                      type="number"
                      className="admin-input-inline"
                      min={1}
                      max={3650}
                      value={row.retention_days}
                      onChange={(e) =>
                        patchRow(row.id, 'retention_days', Number(e.target.value))
                      }
                    />
                    <span className="admin-cell-unit">일</span>
                  </td>
                  <td>
                    <select
                      className="admin-select-inline"
                      value={row.expiry_action}
                      onChange={(e) =>
                        patchRow(row.id, 'expiry_action', e.target.value)
                      }
                    >
                      <option value="delete">삭제</option>
                      <option value="archive">보관</option>
                      <option value="anonymize">익명화</option>
                    </select>
                    <span className="admin-cell-sub">{expiryLabel(row.expiry_action)}</span>
                  </td>
                  <td style={{ textAlign: 'right' }}>
                    {(row.current_count ?? 0).toLocaleString()}
                  </td>
                  <td
                    style={{ textAlign: 'right' }}
                    className={
                      (row.expired_count ?? 0) > 0 ? 'admin-cell-warn' : undefined
                    }
                  >
                    {(row.expired_count ?? 0).toLocaleString()}
                  </td>
                  <td>
                    <label className="admin-check admin-check--compact">
                      <input
                        type="checkbox"
                        checked={row.is_active}
                        onChange={(e) =>
                          patchRow(row.id, 'is_active', e.target.checked)
                        }
                      />
                      {row.is_active ? '적용' : '중지'}
                    </label>
                  </td>
                  <td>
                    <button
                      type="button"
                      className="admin-btn admin-btn--sm"
                      onClick={() =>
                        openDryRun(row.id, `${row.data_label} 드라이런`)
                      }
                    >
                      미리보기
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <div className="admin-card admin-table-wrap admin-mt">
        <div className="admin-card-h">정책 변경 이력 (감사 로그)</div>
        <table>
          <thead>
            <tr>
              <th>일시</th>
              <th>변경 내용</th>
              <th>실행자</th>
            </tr>
          </thead>
          <tbody>
            {history.length === 0 ? (
              <TableEmptyRow colSpan={3} message="변경 이력이 없습니다." />
            ) : (
              history.map((item) => (
                <tr key={item.id}>
                  <td>{new Date(item.created_at).toLocaleString('ko-KR')}</td>
                  <td>{retentionHistorySummary(item)}</td>
                  <td>{item.actor_name || '—'}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <p className="admin-footnote">
        ※ 드라이런은 화면에 입력한 보존 기간·상태를 반영해 미리보기합니다. 실제 삭제는
        실행되지 않습니다. 영상 삭제 시 Chroma 임베딩도 함께 삭제돼야 정합성이 유지됩니다.
      </p>

      <RetentionDryRunModal
        open={dryRunOpen}
        items={dryRunItems}
        title={dryRunTitle}
        loading={dryRunLoading}
        error={dryRunError}
        onClose={() => setDryRunOpen(false)}
      />
    </>
  );
}