/** 동 단위 드릴다운 가능 여부 (시·도·전국 키가 아니면 동 드릴다운 대상) */
import { isSidoKey } from './regionData';

export function hasDongDrilldown(guKey) {
  return Boolean(guKey && guKey !== 'root' && !isSidoKey(guKey));
}
