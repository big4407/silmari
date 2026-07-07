/** 안내문자 미리보기용 간단 파싱 (백엔드 parser와 유사한 정규식) */
export function previewAlertText(text = '') {
  const ageMatch = text.match(/(\d+)\s*세/);
  const genderMatch = text.match(/\(([남여])/);
  const nameMatch =
    text.match(/([가-힣]{2,4})\s*\([남여]/) ||
    text.match(/([가-힣]{2,4})\s*(씨|님|양)/);

  const colors = [
    '빨간',
    '파란',
    '노란',
    '검은',
    '흰',
    '초록',
    '회색',
    '분홍',
    '보라',
    '주황',
  ];
  const foundColors = colors.filter((c) => text.includes(c));

  return {
    name: nameMatch?.[1] || null,
    age: ageMatch ? Number(ageMatch[1]) : null,
    gender: genderMatch
      ? genderMatch[1] === '남'
        ? '남'
        : '여'
      : null,
    clothes: foundColors.length ? foundColors.slice(0, 3).join(', ') : null,
  };
}

export function formatFileSize(bytes) {
  if (!bytes) return '';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
