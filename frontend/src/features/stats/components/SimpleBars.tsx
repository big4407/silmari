import type { DistributionItem } from '../types';

export function SimpleBars({ items }: { items: DistributionItem[] }) {
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
