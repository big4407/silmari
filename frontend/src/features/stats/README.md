# 프론트 통계 기능 모듈

## 기존 코드 변경 범위

1. 기존 라우터 또는 view registry에 통계 화면만 등록합니다.
2. 기존 관리자 메뉴에 경로만 추가합니다.
3. 기존 `StatValue`가 value/loading/decimals props를 받지 않으면
   해당 props를 추가합니다.

React Router 예시:

```tsx
import {
  CctvStatsView,
  DemographicStatsView,
  OutcomeStatsView,
  SearchStatsView,
  StatsExportView,
} from './features/stats';

<Route path="/admin/stats/cctv" element={<CctvStatsView />} />
<Route path="/admin/stats/search" element={<SearchStatsView />} />
<Route
  path="/admin/stats/demographic"
  element={<DemographicStatsView />}
/>
<Route
  path="/admin/stats/outcomes"
  element={<OutcomeStatsView />}
/>
<Route
  path="/admin/stats/export"
  element={<StatsExportView />}
/>
```

`StatsViews.tsx`의 `PageHead`, `EmptyState` import 경로는 현재
프로젝트의 실제 위치에 맞게 한 번 조정하십시오.
