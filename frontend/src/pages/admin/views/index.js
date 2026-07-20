/** 관리자 콘솔 viewId 와 실제 화면 컴포넌트 매핑 */
import { DashboardView } from './DashboardView';
import { MembersPendingView, MembersAllView } from './MemberViews';
import { ReportsView } from './MessageViews';
import { CctvSourceView, SearchRequestsView } from './SearchOpsViews';
import { LlmUsageView } from './LlmViews';
import {
  CctvStatsView,
  SearchStatsView,
  DemographicStatsView,
  OutcomeStatsView,
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
  'stats-cctv': CctvStatsView,
  'stats-search': SearchStatsView,
  'stats-demographic': DemographicStatsView,
  'stats-outcomes': OutcomeStatsView,
  'stats-export': StatsExportView,
  'data-codes': DataCodesView,
  'data-validate': DataValidateView,
  'data-retention': DataRetentionView,
  'audit-admin': AuditAdminView,
  'audit-approval': AuditApprovalView,
  'audit-login': AuditLoginView,
};
