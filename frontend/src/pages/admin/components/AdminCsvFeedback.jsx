/** CSV보내기·가져오기 등 툴바 작업 결과 안내 */
export default function AdminCsvFeedback({ feedback }) {
  if (!feedback?.text) return null;
  if (feedback.type === 'success') {
    return (
      <p className="admin-inline-ok admin-mb" role="status" aria-live="polite">
        {feedback.text}
      </p>
    );
  }
  return (
    <p
      className="admin-modal__error admin-modal__error--inline admin-mb"
      role="alert"
    >
      {feedback.text}
    </p>
  );
}
