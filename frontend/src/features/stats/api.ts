import client, {
  readApiErrorMessage,
  saveBlobDownload,
} from '../../api/client';

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

function buildParams(query: Query = {}) {
  return {
    from_date: query.fromDate || undefined,
    to_date: query.toDate || undefined,
    region: query.region || undefined,
    search_type: query.searchType || undefined,
  };
}

async function toError(
  error: unknown,
  fallback: string,
): Promise<Error> {
  const message = await readApiErrorMessage(error, fallback);
  return new Error(message);
}

async function getJson<T>(
  path: string,
  query?: Query,
  signal?: AbortSignal,
): Promise<T> {
  try {
    const response = await client.get(`${BASE_URL}${path}`, {
      params: buildParams(query),
      signal,
    });
    return response.data;
  } catch (error) {
    throw await toError(error, '통계 데이터를 불러오지 못했습니다.');
  }
}

export function fetchCctvStats(
  query: Query,
  signal?: AbortSignal,
): Promise<CctvStatsResponse> {
  return getJson<CctvStatsResponse>('/cctv', query, signal);
}

export function fetchSearchStats(
  query: Query,
  signal?: AbortSignal,
): Promise<SearchStatsResponse> {
  return getJson<SearchStatsResponse>('/search', query, signal);
}

export function fetchDemographicStats(
  query: Query,
  signal?: AbortSignal,
): Promise<DemographicStatsResponse> {
  return getJson<DemographicStatsResponse>('/demographic', query, signal);
}

export function fetchOutcomeStats(
  query: Query,
  signal?: AbortSignal,
): Promise<OutcomeStatsResponse> {
  return getJson<OutcomeStatsResponse>('/outcomes', query, signal);
}

export async function createCaseEvent(
  payload: CaseEventCreate,
): Promise<CaseEvent> {
  try {
    const response = await client.post(`${BASE_URL}/case-events`, payload);
    return response.data;
  } catch (error) {
    throw await toError(error, '이벤트 저장에 실패했습니다.');
  }
}

export function fetchExportLogs(signal?: AbortSignal): Promise<ExportLog[]> {
  return getJson<ExportLog[]>('/exports', undefined, signal);
}

export async function exportStats(payload: {
  stat_type: StatType;
  from_date: string;
  to_date: string;
  region?: string;
  search_type?: string;
}): Promise<void> {
  try {
    const response = await client.post(
      `${BASE_URL}/export`,
      {
        ...payload,
        file_format: 'CSV',
      },
      {
        responseType: 'blob',
      },
    );

    const disposition = response.headers?.['content-disposition'] ?? '';
    const match = String(disposition).match(/filename="([^"]+)"/);
    const filename = match?.[1] ?? 'statistics.csv';
    saveBlobDownload(response.data, filename);
  } catch (error) {
    throw await toError(error, '통계 내보내기에 실패했습니다.');
  }
}
