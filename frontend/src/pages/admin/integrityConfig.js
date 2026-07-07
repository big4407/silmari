/** 정합성 검사 — 대상 라벨·관리 화면 바로가기 */

export const INTEGRITY_TARGET_LABELS = {
  region: '행정구역',
  video: '영상',
  auth: '인증',
  search: '검색',
  analysis: '분석',
};

export const INTEGRITY_TARGET_OPTIONS = [
  { value: '', label: '전체 대상' },
  { value: 'region', label: '행정구역' },
  { value: 'video', label: '영상' },
  { value: 'auth', label: '인증' },
  { value: 'search', label: '검색' },
  { value: 'analysis', label: '분석' },
];

export const INTEGRITY_STATUS_OPTIONS = [
  { value: '', label: '전체 결과' },
  { value: 'issues', label: '주의 이상' },
  { value: 'error', label: '오류만' },
  { value: 'warn', label: '주의만' },
];

const TARGET_LINKS = {
  region: { viewId: 'data-codes', label: '기준 코드 관리' },
  video: { viewId: 'cctv-source', label: 'CCTV 영상 수집' },
  auth: { viewId: 'members-all', label: '전체 회원' },
  search: { viewId: 'search-requests', label: '검색 요청 이력' },
  analysis: { viewId: 'search-jobs', label: '검색 작업 현황' },
};

const CHECK_LINKS = {
  video_orphan_region: { viewId: 'cctv-source', label: 'CCTV 영상 수집' },
  video_detail_orphan_video: { viewId: 'cctv-source', label: 'CCTV 영상 수집' },
  session_orphan_user: { viewId: 'audit-login', label: '로그인·접근 이력' },
  session_expired_active: { viewId: 'audit-login', label: '로그인·접근 이력' },
  login_orphan_user: { viewId: 'audit-login', label: '로그인·접근 이력' },
};

export function integrityTargetLabel(target) {
  return INTEGRITY_TARGET_LABELS[target] || target;
}

export function integrityFixLink(check) {
  if (!check) return null;
  return CHECK_LINKS[check.check_id] || TARGET_LINKS[check.target] || null;
}

export function integrityStatusLabel(status) {
  if (status === 'ok') return '정상';
  if (status === 'warn') return '주의';
  return '오류';
}

export function integrityStatusClass(status) {
  if (status === 'ok') return 'admin-pill admin-pill--ok';
  if (status === 'warn') return 'admin-pill admin-pill--warn';
  return 'admin-pill admin-pill--danger';
}

export function historyItemToIntegrityResult(item) {
  const d = item?.detail || {};
  if (d.action !== 'run') return null;
  return {
    ran_at: item.created_at,
    total_issues: d.total_issues ?? 0,
    checks: d.checks ?? [],
    delta_issues: d.delta_issues ?? null,
    run_id: item.id,
  };
}

function csvEscape(value) {
  const text = String(value ?? '');
  if (/[",\n\r]/.test(text)) return `"${text.replace(/"/g, '""')}"`;
  return text;
}

export function checksToCsvBlob(checks) {
  const header = [
    'check_id',
    'label',
    'target',
    'status',
    'issue_count',
    'description',
    'samples',
  ];
  const lines = [
    header.join(','),
    ...checks.map((c) =>
      [
        c.check_id,
        c.label,
        c.target,
        c.status,
        c.issue_count,
        c.description,
        (c.samples || []).join('; '),
      ]
        .map(csvEscape)
        .join(','),
    ),
  ];
  return new Blob(['\ufeff', lines.join('\n')], {
    type: 'text/csv;charset=utf-8',
  });
}

export function issuesToCsvBlob(check, issues) {
  const lines = [
    ['check_id', 'label', 'issue'].map(csvEscape).join(','),
    ...issues.map((issue) =>
      [check.check_id, check.label, issue].map(csvEscape).join(','),
    ),
  ];
  return new Blob(['\ufeff', lines.join('\n')], {
    type: 'text/csv;charset=utf-8',
  });
}
