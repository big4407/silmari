/** 일별 검색 추이 꺾은선 그래프 */
export function SimpleLineChart({ data }) {
  if (data.length === 0) {
    return <div className="stats-empty">통계 데이터가 없습니다.</div>;
  }

  const width = 640;
  const height = 220;
  const padding = 28;
  const maxValue = Math.max(...data.map((item) => item.search_count), 1);
  const denominator = Math.max(data.length - 1, 1);

  const points = data
    .map((item, index) => {
      const x = padding + (index / denominator) * (width - padding * 2);
      const y =
        height - padding - (item.search_count / maxValue) * (height - padding * 2);
      return `${x},${y}`;
    })
    .join(' ');

  return (
    <div className="stats-chart-wrap">
      <svg
        viewBox={`0 0 ${width} ${height}`}
        role="img"
        aria-label="일별 검색 추이"
        className="stats-line-chart"
      >
        <line
          x1={padding}
          y1={height - padding}
          x2={width - padding}
          y2={height - padding}
          className="stats-line-chart__axis"
        />
        <polyline points={points} fill="none" className="stats-line-chart__line" />
        {data.map((item, index) => {
          const x = padding + (index / denominator) * (width - padding * 2);
          const y =
            height - padding - (item.search_count / maxValue) * (height - padding * 2);

          return (
            <circle
              key={item.date}
              cx={x}
              cy={y}
              r={3}
              className="stats-line-chart__point"
            >
              <title>
                {item.date}: 검색 {item.search_count}건, 성공 {item.successful_count}건
              </title>
            </circle>
          );
        })}
      </svg>
    </div>
  );
}
