/** 버튼·라벨 처리 중 스피너 + 문구 */
export default function AdminBusyLabel({
  busy,
  idle,
  busyLabel = '처리 중…',
}) {
  if (!busy) return idle;
  return (
    <>
      <span className="admin-spinner" aria-hidden="true" />
      {busyLabel}
    </>
  );
}
