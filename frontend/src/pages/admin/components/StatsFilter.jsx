/** 통계 화면 공용 필터 — 기간·지역·검색유형 */
export function StatsFilter({
  periodDays,
  onPeriodDaysChange,
  region,
  onRegionChange,
  searchType,
  onSearchTypeChange,
}) {
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
          <option value="1">안내문자</option>
          <option value="2">챗봇</option>
          <option value="3">자동 검색</option>
        </select>
      )}

      <div className="admin-spacer" />
    </div>
  );
}
