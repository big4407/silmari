import { REGION_DATA } from "../hooks/useMapDrilldown"

/** 시도 약칭 → rcptn_rgn_nm 매칭용 키워드 */
export const SIDO_SEARCH_TERMS = {
  서울: ["서울특별시", "서울"],
  부산: ["부산광역시", "부산"],
  대구: ["대구광역시", "대구"],
  인천: ["인천광역시", "인천"],
  광주: ["광주광역시", "광주"],
  대전: ["대전광역시", "대전"],
  울산: ["울산광역시", "울산"],
  세종: ["세종특별자치시", "세종"],
  경기: ["경기도", "경기"],
  강원: ["강원특별자치도", "강원도", "강원"],
  충북: ["충청북도", "충북"],
  충남: ["충청남도", "충남"],
  전북: ["전북특별자치도", "전라북도", "전북"],
  전남: ["전라남도", "전남"],
  경북: ["경상북도", "경북"],
  경남: ["경상남도", "경남"],
  제주: ["제주특별자치도", "제주"],
}

export function buildMapFilter(region, path) {
  if (!region || path.length <= 1) {
    return { level: "nation" }
  }
  const sidoId = path[1]
  const isSido = REGION_DATA.root.regions.some(r => r.id === region.id)
  if (isSido) {
    return { level: "sido", label: region.label, sidoId: region.id }
  }
  const sidoLabel = REGION_DATA[sidoId]?.label
    || REGION_DATA.root.regions.find(r => r.id === sidoId)?.label
    || ""
  return { level: "gu", label: region.label, sidoId, sidoLabel }
}

export function alertMatchesFilter(rcptnRgnNm, mapFilter) {
  const text = (rcptnRgnNm || "").trim()
  if (!text || !mapFilter || mapFilter.level === "nation") return true

  const sidoTerms = SIDO_SEARCH_TERMS[mapFilter.sidoLabel || mapFilter.label] || [mapFilter.label]

  if (mapFilter.level === "sido") {
    return sidoTerms.some(term => text.includes(term))
  }

  if (mapFilter.level === "gu") {
    return text.includes(mapFilter.label) && sidoTerms.some(term => text.includes(term))
  }

  return true
}

export function filterAlertsByRegion(alerts, mapFilter) {
  if (!mapFilter || mapFilter.level === "nation") return alerts
  return alerts.filter(a => alertMatchesFilter(a.rcptn_rgn_nm, mapFilter))
}

export function countAlertsForSido(alerts, sidoLabel) {
  const filter = { level: "sido", label: sidoLabel }
  return filterAlertsByRegion(alerts, filter).length
}

/** 안내문자 rcptn_rgn_nm → 지도 포커스 정보 */
export function resolveAlertMapFocus(rcptnRgnNm) {
  const text = (rcptnRgnNm || "").trim()
  if (!text) return null

  let matchedSido = null
  for (const region of REGION_DATA.root.regions) {
    const terms = SIDO_SEARCH_TERMS[region.label] || [region.label]
    if (terms.some(term => text.includes(term))) {
      matchedSido = region
      break
    }
  }
  if (!matchedSido) return null

  const sidoData = REGION_DATA[matchedSido.id]
  if (sidoData?.regions) {
    for (const gu of sidoData.regions) {
      if (text.includes(gu.label)) {
        return {
          path: ["root", matchedSido.id],
          selectedLabel: gu.label,
          center: [gu.lat, gu.lng],
          zoom: 13,
        }
      }
    }
  }

  return {
    path: ["root", matchedSido.id],
    selectedLabel: matchedSido.label,
    center: [matchedSido.lat, matchedSido.lng],
    zoom: sidoData?.zoom || 10,
  }
}
