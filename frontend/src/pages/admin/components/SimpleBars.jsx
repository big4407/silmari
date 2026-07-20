/** 성별/연령 분포 등 단순 막대그래프 */
export function SimpleBars({ items }) {
  if (items.length === 0) {
    return <div className="stats-empty">통계 데이터가 없습니다.</div>;
  }

  return (
    <div className="stats-bars">
      {items.map((item) => (
        <div className="stats-bars__row" key={item.label}>
          <div className="stats-bars__header">
            <span>{item.label}</span>
            <strong>
              {item.count.toLocaleString()}건 ({item.ratio.toFixed(1)}%)
            </strong>
          </div>
          <div className="stats-bars__track">
            <div
              className="stats-bars__fill"
              style={{ width: `${Math.min(item.ratio, 100)}%` }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}
