/** 아직 구현되지 않은보내기·필터 등 — 비활성 버튼 대신 표시 */
export default function AdminFeaturePending({ label = 'CSV보내기' }) {
  return (
    <span className="admin-feature-pending" role="status">
      {label} — 준비 중
    </span>
  );
}
