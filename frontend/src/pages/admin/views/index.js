import { DashboardView } from "./DashboardView"
import { MembersPendingView, MembersAllView } from "./MemberViews"
import { ReportsView, ParseReviewView } from "./MessageViews"
import {
  CctvSourceView,
  SearchRequestsView,
  SearchJobsView,
  MatchReviewView,
} from "./SearchOpsViews"
import { LlmUsageView, LlmCostView, LlmPerfView, LlmLogsView } from "./LlmViews"
import { RepTimeView, RepRegionView, RepSearchView } from "./ReportViews"
import {
  DataCodesView,
  DataValidateView,
  DataExportView,
  DataRetentionView,
} from "./DataViews"
import { AuditAdminView, AuditApprovalView, AuditLoginView } from "./AuditViews"

export const ADMIN_VIEWS = {
  dashboard: DashboardView,
  "members-pending": MembersPendingView,
  "members-all": MembersAllView,
  reports: ReportsView,
  "parse-review": ParseReviewView,
  "cctv-source": CctvSourceView,
  "search-requests": SearchRequestsView,
  "search-jobs": SearchJobsView,
  "match-review": MatchReviewView,
  "llm-usage": LlmUsageView,
  "llm-cost": LlmCostView,
  "llm-perf": LlmPerfView,
  "llm-logs": LlmLogsView,
  "rep-time": RepTimeView,
  "rep-region": RepRegionView,
  "rep-search": RepSearchView,
  "data-codes": DataCodesView,
  "data-validate": DataValidateView,
  "data-export": DataExportView,
  "data-retention": DataRetentionView,
  "audit-admin": AuditAdminView,
  "audit-approval": AuditApprovalView,
  "audit-login": AuditLoginView,
}
