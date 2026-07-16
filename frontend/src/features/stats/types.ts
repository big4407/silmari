export interface Period {
  from_date: string;
  to_date: string;
}

export interface CctvStatsResponse {
  period: Period;
  summary: {
    registered_videos: number;
    indexed_videos: number;
    detected_persons: number;
    covered_regions: number;
  };
  by_region: Array<{
    region: string;
    registered_videos: number;
    indexed_videos: number;
    detected_persons: number;
  }>;
}

export interface SearchStatsResponse {
  period: Period;
  summary: {
    total_searches: number;
    successful_matches: number;
    average_similarity_percent: number;
    average_processing_seconds: number;
  };
  by_type: Array<{
    search_type: string;
    count: number;
    successful_matches: number;
    success_rate: number;
  }>;
  daily: Array<{
    date: string;
    search_count: number;
    successful_count: number;
  }>;
}

export interface DemographicStatsResponse {
  period: Period;
  gender_distribution: DistributionItem[];
  age_distribution: DistributionItem[];
  by_region: Array<{
    region: string;
    search_requests: number;
    found_cases: number;
    resolved_cases: number;
    finding_rate: number;
    resolution_rate: number;
  }>;
}

export interface DistributionItem {
  label: string;
  count: number;
  ratio: number;
}

export type CaseEventType = 'FOUND' | 'RESOLVED';

export interface CaseEvent {
  id: number;
  case_key: string;
  event_type: CaseEventType;
  occurred_at: string;
  reported_at: string | null;
  region: string | null;
  actor_name: string | null;
  actor_role: string | null;
  recorded_by_name: string;
  location_text: string | null;
  source_search_id: number | null;
  source_analysis_id: number | null;
  source_analysis_detail_id: number | null;
  note: string | null;
  created_at: string;
}

export interface OutcomeStatsResponse {
  period: Period;
  summary: {
    found_cases: number;
    resolved_cases: number;
    resolution_after_found_rate: number;
    average_hours_to_find: number | null;
    average_hours_to_resolve: number | null;
  };
  by_region: Array<{
    region: string;
    found_cases: number;
    resolved_cases: number;
    resolution_rate: number;
  }>;
  recent_records: CaseEvent[];
}

export interface CaseEventCreate {
  case_key?: string;
  event_type: CaseEventType;
  occurred_at: string;
  actor_id?: number;
  actor_name?: string;
  actor_role?: string;
  location_text?: string;
  latitude?: number;
  longitude?: number;
  region?: string;
  source_search_id?: number;
  source_analysis_id?: number;
  source_analysis_detail_id?: number;
  reported_at?: string;
  note?: string;
}

export type StatType =
  | 'cctv'
  | 'search'
  | 'demographic'
  | 'outcomes';

export interface ExportLog {
  id: number;
  stat_type: string;
  from_date: string;
  to_date: string;
  file_format: string;
  file_name: string;
  row_count: number;
  requested_by_name: string;
  created_at: string;
}
