interface StatsFilterProps {
  periodDays: number;
  onPeriodDaysChange: (days: number) => void;
  region?: string;
  onRegionChange?: (region: string) => void;
  searchType?: string;
  onSearchTypeChange?: (searchType: string) => void;
}

export function StatsFilter({
  periodDays,
  onPeriodDaysChange,
  region,
  onRegionChange,
  searchType,
  onSearchTypeChange,
}: StatsFilterProps) {
  return (
    <div className="admin-toolbar">
      <select
        value={periodDays}
        onChange={(event) => onPeriodDaysChange(Number(event.target.value))}
      >
        <option value={7}>최근 7일</option>
        <option value={30}>최근 30일</option>
        <option value={90}>최근 90일</option>
        <option value={365}>최근 1년</option>
      </select>

      {onRegionChange && (
        <input
          type="search"
          value={region ?? ''}
          placeholder="전체 지역"
          onChange={(event) => onRegionChange(event.target.value)}
        />
      )}

      {onSearchTypeChange && (
        <select
          value={searchType ?? ''}
          onChange={(event) => onSearchTypeChange(event.target.value)}
        >
          <option value="">전체 검색 유형</option>
          <option value="IMAGE">이미지</option>
          <option value="TEXT">텍스트</option>
          <option value="HYBRID">하이브리드</option>
        </select>
      )}

      <div className="admin-spacer" />
    </div>
  );
}
