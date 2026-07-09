/** 지역명 검색 → 지도 포커스·mapFilter 변환 */
import * as adk from 'admdongkor';
import { REGION_DATA } from '../data/regionData';
import { REGION_SIDO_FROM_ADM } from './admDongLoader';
import { SIDO_SEARCH_TERMS, buildMapFilter } from './regionMatch';

function normalize(text) {
  return (text || '').trim().replace(/\s/g, '');
}

function matchesSido(query, sido) {
  const q = normalize(query);
  if (!q) return false;

  const label = normalize(sido.label);
  if (label.includes(q) || q.includes(label)) return true;

  const terms = SIDO_SEARCH_TERMS[sido.label] || [];
  return terms.some((term) => {
    const t = normalize(term);
    return (
      t.includes(q) ||
      q.includes(t) ||
      t.includes(q.replace(/특별|광역|자치/g, ''))
    );
  });
}

function matchesGu(query, gu) {
  const q = normalize(query);
  const label = normalize(gu.label);
  if (!label || !q) return false;
  if (label.includes(q) || q.includes(label)) return true;

  const short = label.replace(/(특별|광역)?시|구|군$/g, '');
  return short.length >= 2 && (short.includes(q) || q.includes(short));
}

function focusFromAdmRow(row) {
  const sidoId = REGION_SIDO_FROM_ADM[row.sidocd];
  if (!sidoId) return null;

  if (row.level === 'emd' && row.sggnm) {
    const gu = REGION_DATA[sidoId]?.regions?.find(
      (r) => normalize(r.label) === normalize(row.sggnm),
    ) || { id: row.sggcd || row.sggnm, label: row.sggnm };
    const path = ['root', sidoId, gu.id];
    const dong = { id: row.code, label: row.name, guLabel: row.sggnm };
    return {
      path,
      selectedLabel: row.name,
      dongId: row.code,
      guLabel: row.sggnm,
      mapFilter: buildMapFilter(dong, path),
    };
  }

  if (row.level === 'sgg') {
    const gu = REGION_DATA[sidoId]?.regions?.find(
      (r) => normalize(r.label) === normalize(row.name),
    ) || { id: row.code, label: row.name };
    const path = ['root', sidoId];
    return {
      path,
      selectedLabel: gu.label,
      mapFilter: buildMapFilter(gu, path),
    };
  }

  return null;
}

/** 지역명 검색 → 지도 포커스 정보 (없으면 null) */
export async function findRegionByName(query) {
  const q = normalize(query);
  if (!q) return null;

  try {
    const rows = await adk.find(query.trim(), { year: [2025] });
    const emdRows = rows.filter((r) => r.level === 'emd');
    if (emdRows.length > 0) {
      const focus = focusFromAdmRow(emdRows[emdRows.length - 1]);
      if (focus) return focus;
    }

    const sggRows = rows.filter((r) => r.level === 'sgg');
    if (sggRows.length > 0) {
      const focus = focusFromAdmRow(sggRows[sggRows.length - 1]);
      if (focus) return focus;
    }
  } catch {
    // admdongkor unavailable — fall through to static lookup
  }

  for (const sido of REGION_DATA.root.regions) {
    const sidoData = REGION_DATA[sido.id];
    if (!sidoData?.regions) continue;

    for (const gu of sidoData.regions) {
      if (matchesGu(q, gu)) {
        const path = ['root', sido.id];
        return {
          path,
          selectedLabel: gu.label,
          mapFilter: buildMapFilter(gu, path),
        };
      }
    }
  }

  for (const sido of REGION_DATA.root.regions) {
    if (matchesSido(q, sido)) {
      const path = ['root', sido.id];
      return {
        path,
        selectedLabel: sido.label,
        mapFilter: buildMapFilter(sido, path),
      };
    }
  }

  return null;
}
