/**
 * 앱 전체에서 말줄임표(text-overflow: ellipsis)로 잘린 요소에 마우스를
 * 올렸을 때 자동으로 title 속성을 붙여서 전체 내용이 보이게 한다.
 *
 * 특정 클래스(.admin-console 등)에 스코프하지 않고, 실제로 CSS
 * ellipsis 처리가 적용된 요소인지를 getComputedStyle로 직접 판별한다 —
 * 그래서 관리자 콘솔의 테이블 셀뿐 아니라, 대시보드 카드·검색 이력 등
 * 어디서 새로 ellipsis를 쓰든 이 코드를 따로 안 건드려도 자동으로 커버된다.
 *
 * - mouseover 이벤트 위임(document에 리스너 하나) — 요소마다 따로 안 붙임.
 * - 실제로 잘린(overflow) 요소에만 title을 붙인다.
 * - 개발자가 이미 title을 직접 넣어둔 요소는 그 값을 존중하고 덮어쓰지 않는다.
 * - App.jsx 최상단에서 한 번만 초기화하면 앱 전체(관리자 포함)에 적용된다.
 */
function isEllipsisTruncated(el) {
  const style = getComputedStyle(el);
  const usesEllipsis =
    style.textOverflow === 'ellipsis' || style.webkitLineClamp !== 'none';
  if (!usesEllipsis || style.overflow === 'visible') return false;

  // 한 줄 말줄임표: 가로로 잘림 / 여러 줄 클램프(-webkit-line-clamp): 세로로 잘림
  return el.scrollWidth > el.clientWidth || el.scrollHeight > el.clientHeight;
}

export function initAutoTitle() {
  const handleMouseOver = (event) => {
    // title을 붙일 대상 후보를 찾아 위로 올라가며 확인한다(최대 6단계 —
    // 너무 깊이 올라가서 무관한 조상까지 검사하지 않도록 제한).
    let el = event.target;
    let depth = 0;
    while (el && el.nodeType === 1 && depth < 6) {
      if (el.title) return; // 이미 title 있음 — 존중하고 종료
      if (isEllipsisTruncated(el)) {
        const text = el.textContent?.trim();
        if (text) el.title = text;
        return;
      }
      el = el.parentElement;
      depth += 1;
    }
  };

  document.addEventListener('mouseover', handleMouseOver);

  return () => {
    document.removeEventListener('mouseover', handleMouseOver);
  };
}
