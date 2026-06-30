/** 지역명 검색 → 지도 포커스·mapFilter 변환 */
import { REGION_DATA } from "../hooks/useMapDrilldown"
import { hasDongDrilldown } from "../data/dongRegions"
import { SIDO_SEARCH_TERMS, buildMapFilter } from "./regionMatch"

function normalize(text) {
  return (text || "").trim().replace(/\s/g, "")
}

function matchesSido(query, sido) {
  const q = normalize(query)
  if (!q) return false

  const label = normalize(sido.label)
  if (label.includes(q) || q.includes(label)) return true

  const terms = SIDO_SEARCH_TERMS[sido.label] || []
  return terms.some((term) => {
    const t = normalize(term)
    return t.includes(q) || q.includes(t) || t.includes(q.replace(/특별|광역|자치/g, ""))
  })
}

function matchesGu(query, gu) {
  const q = normalize(query)
  const label = normalize(gu.label)
  if (!label || !q) return false
  if (label.includes(q) || q.includes(label)) return true

  const short = label.replace(/(특별|광역)?시|구|군$/g, "")
  return short.length >= 2 && (short.includes(q) || q.includes(short))
}

function matchesDong(query, dong) {
  const q = normalize(query)
  const label = normalize(dong.label)
  if (!label || !q) return false
  return label.includes(q) || q.includes(label)
}

/** 지역명 검색 → 지도 포커스 정보 (없으면 null) */
export function findRegionByName(query) {
  const q = normalize(query)
  if (!q) return null

  for (const sido of REGION_DATA.root.regions) {
    const sidoData = REGION_DATA[sido.id]
    if (!sidoData?.regions) continue

    for (const gu of sidoData.regions) {
      if (!hasDongDrilldown(gu.id)) continue
      const dongData = REGION_DATA[gu.id]
      for (const dong of dongData?.regions || []) {
        if (matchesDong(q, dong)) {
          const path = ["root", sido.id, gu.id]
          return {
            path,
            selectedLabel: dong.label,
            mapFilter: buildMapFilter(dong, path),
          }
        }
      }
    }
  }

  for (const sido of REGION_DATA.root.regions) {
    const sidoData = REGION_DATA[sido.id]
    if (!sidoData?.regions) continue

    for (const gu of sidoData.regions) {
      if (matchesGu(q, gu)) {
        const path = ["root", sido.id]
        return {
          path,
          selectedLabel: gu.label,
          mapFilter: buildMapFilter(gu, path),
        }
      }
    }
  }

  for (const sido of REGION_DATA.root.regions) {
    if (matchesSido(q, sido)) {
      const path = ["root", sido.id]
      return {
        path,
        selectedLabel: sido.label,
        mapFilter: buildMapFilter(sido, path),
      }
    }
  }

  return null
}
