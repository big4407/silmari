export function formatDateInput(date: Date): string {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(
    2,
    '0',
  );
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

export function recentDateRange(days: number): {
  fromDate: string;
  toDate: string;
} {
  const toDate = new Date();
  const fromDate = new Date();
  fromDate.setDate(toDate.getDate() - days + 1);

  return {
    fromDate: formatDateInput(fromDate),
    toDate: formatDateInput(toDate),
  };
}

export function formatDateTime(value: string): string {
  return new Intl.DateTimeFormat('ko-KR', {
    dateStyle: 'short',
    timeStyle: 'short',
  }).format(new Date(value));
}
