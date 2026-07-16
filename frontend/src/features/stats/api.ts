import type {
  CaseEvent,
  CaseEventCreate,
  CctvStatsResponse,
  DemographicStatsResponse,
  ExportLog,
  OutcomeStatsResponse,
  SearchStatsResponse,
  StatType,
} from './types';

const BASE_URL = '/api/v1/admin/stats';

interface Query {
  fromDate?: string;
  toDate?: string;
  region?: string;
  searchType?: string;
}

function buildQuery(query: Query): string {
  const params = new URLSearchParams();

  if (query.fromDate) {
    params.set('from_date', query.fromDate);
  }
  if (query.toDate) {
    params.set('to_date', query.toDate);
  }
  if (query.region) {
    params.set('region', query.region);
  }
  if (query.searchType) {
    params.set('search_type', query.searchType);
  }

  const text = params.toString();
  return text ? `?${text}` : '';
}

async function parseError(response: Response): Promise<Error> {
  const body = await response.json().catch(() => null);
  return new Error(body?.detail ?? `요청 실패 (${response.status})`);
}

async function getJson<T>(path: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, {
    method: 'GET',
    credentials: 'include',
    headers: {
      Accept: 'application/json',
    },
    signal,
  });

  if (!response.ok) {
    throw await parseError(response);
  }

  return response.json();
}

export function fetchCctvStats(
  query: Query,
  signal?: AbortSignal,
): Promise<CctvStatsResponse> {
  return getJson<CctvStatsResponse>(`/cctv${buildQuery(query)}`, signal);
}

export function fetchSearchStats(
  query: Query,
  signal?: AbortSignal,
): Promise<SearchStatsResponse> {
  return getJson<SearchStatsResponse>(`/search${buildQuery(query)}`, signal);
}

export function fetchDemographicStats(
  query: Query,
  signal?: AbortSignal,
): Promise<DemographicStatsResponse> {
  return getJson<DemographicStatsResponse>(
    `/demographic${buildQuery(query)}`,
    signal,
  );
}

export function fetchOutcomeStats(
  query: Query,
  signal?: AbortSignal,
): Promise<OutcomeStatsResponse> {
  return getJson<OutcomeStatsResponse>(`/outcomes${buildQuery(query)}`, signal);
}

export async function createCaseEvent(
  payload: CaseEventCreate,
): Promise<CaseEvent> {
  const response = await fetch(`${BASE_URL}/case-events`, {
    method: 'POST',
    credentials: 'include',
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw await parseError(response);
  }

  return response.json();
}

export function fetchExportLogs(signal?: AbortSignal): Promise<ExportLog[]> {
  return getJson<ExportLog[]>('/exports', signal);
}

export async function exportStats(payload: {
  stat_type: StatType;
  from_date: string;
  to_date: string;
  region?: string;
  search_type?: string;
}): Promise<void> {
  const response = await fetch(`${BASE_URL}/export`, {
    method: 'POST',
    credentials: 'include',
    headers: {
      Accept: 'text/csv',
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      ...payload,
      file_format: 'CSV',
    }),
  });

  if (!response.ok) {
    throw await parseError(response);
  }

  const blob = await response.blob();
  const disposition = response.headers.get('Content-Disposition') ?? '';
  const match = disposition.match(/filename="([^"]+)"/);
  const filename = match?.[1] ?? 'statistics.csv';

  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}
