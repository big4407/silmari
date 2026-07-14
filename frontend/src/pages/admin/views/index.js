/** 관리자 콘솔 뷰 컴포넌트 레지스트리 — viewId → React 컴포넌트 */
import { DashboardView } from './DashboardView';
import { MembersPendingView, MembersAllView } from './MemberViews';
import { ReportsView } from './MessageViews';
import { CctvSourceView, SearchRequestsView } from './SearchOpsViews';
import { LlmUsageView, LlmLogsView } from './LlmViews';
import {
  CctvStatsView,
  SearchStatsView,
  DemographicStatsView,
  StatsExportView,
} from './StatsViews';
import {
  DataCodesView,
  DataValidateView,
  DataRetentionView,
} from './DataViews';
import {
  AuditAdminView,
  AuditApprovalView,
  AuditLoginView,
} from './AuditViews';

export const ADMIN_VIEWS = {
  dashboard: DashboardView,
  'members-pending': MembersPendingView,
  'members-all': MembersAllView,
  reports: ReportsView,
  'cctv-source': CctvSourceView,
  'search-requests': SearchRequestsView,
  'llm-usage': LlmUsageView,
  'llm-logs': LlmLogsView,
  'stats-cctv': CctvStatsView,
  'stats-search': SearchStatsView,
  'stats-demographic': DemographicStatsView,
  'stats-export': StatsExportView,
  'data-codes': DataCodesView,
  'data-validate': DataValidateView,
  'data-retention': DataRetentionView,
  'audit-admin': AuditAdminView,
  'audit-approval': AuditApprovalView,
  'audit-login': AuditLoginView,
};
