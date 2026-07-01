/**
 * 지역명 ↔ 재난문자 rcptn_rgn_nm 매칭·필터 유틸.
 * Dashboard 지도 선택 → alertList 필터링에 사용.
 */
import { REGION_DATA } from "../data/regionData"
import { hasDongDrilldown } from "../data/dongRegions"

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
  if (path.length > 2 && hasDongDrilldown(path[2])) {
    const guId = path[2]
    const guMeta = REGION_DATA[sidoId]?.regions?.find(r => r.id === guId)
    const guLabel = guMeta?.label || region.guLabel || ""
    if (region.id === guId || (guMeta && region.id === guMeta.id)) {
      return { level: "gu", label: region.label, sidoId, sidoLabel }
    }
    return {
      level: "dong",
      label: region.label,
      guId,
      guLabel,
      sidoId,
      sidoLabel,
    }
  }
  return { level: "gu", label: region.label, sidoId, sidoLabel }
}

export function alertMatchesFilter(rcptnRgnNm, mapFilter) {
  const text = (rcptnRgnNm || "").trim()
  if (!text || !mapFilter || mapFilter.level === "nation") return true

  const sidoTerms = SIDO_SEARCH_TERMS[mapFilter.sidoLabel || mapFilter.label] || [mapFilter.label]
  if (!sidoTerms.some(term => text.includes(term))) return false

  if (mapFilter.level === "sido") {
    return true
  }

  if (mapFilter.level === "gu") {
    const label = mapFilter.label.replace(/\s/g, "")
    const textNorm = text.replace(/\s/g, "")
    if (textNorm.includes(label)) return true

    const cityGu = label.match(/^(.+시)(.+[구군])$/)
    if (cityGu && textNorm.includes(cityGu[1]) && textNorm.includes(cityGu[2])) {
      return true
    }

    const city = label.match(/^(.+시)/)?.[1]
    if (city && textNorm.includes(city)) return true

    return text.includes(mapFilter.label)
  }

  if (mapFilter.level === "dong") {
    const textNorm = text.replace(/\s/g, "")
    const dongLabel = mapFilter.label.replace(/\s/g, "")
    if (dongLabel && textNorm.includes(dongLabel)) return true
    const guLabel = (mapFilter.guLabel || "").replace(/\s/g, "")
    if (guLabel && textNorm.includes(guLabel)) return true
    return false
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

/** rcptn_rgn_nm에서 읍·면·동 후보 추출 */
function extractEmdNames(text) {
  return [...text.matchAll(/([가-힣0-9]+(?:동|읍|면))/g)].map(m => m[1])
}

function isSidoUnit(name, matchedSido) {
  const sidoTerms = SIDO_SEARCH_TERMS[matchedSido.label] || [matchedSido.label]
  return sidoTerms.some(term => name.includes(term.replace(/도$|특별.*$|광역.*$/, "")))
}

/** rcptn_rgn_nm에서 시·군·구 추출 (북구 단독 매칭 방지) */
function extractSubRegion(text, matchedSido) {
  const cityGuMatches = [...text.matchAll(/([가-힣]+시)\s*([가-힣]+[구군])/g)]
    .filter(([, city]) => !isSidoUnit(city, matchedSido))

  if (cityGuMatches.length > 0) {
    const first = cityGuMatches[0]
    return `${first[1]} ${first[2]}`
  }

  const cityMatches = [...text.matchAll(/([가-힣]+(?:시|군))/g)]
    .map(m => m[1])
    .filter(name => !isSidoUnit(name, matchedSido))
  if (cityMatches.length > 0) {
    return cityMatches[cityMatches.length - 1]
  }

  return null
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

  const path = ["root", matchedSido.id]
  const sidoData = REGION_DATA[matchedSido.id]

  if (sidoData?.regions) {
    for (const gu of sidoData.regions) {
      if (text.includes(gu.label)) {
        if (hasDongDrilldown(gu.id)) {
          for (const emdName of extractEmdNames(text)) {
            if (text.includes(emdName)) {
              const dongPath = [...path, gu.id]
              const dong = { id: emdName, label: emdName }
              return {
                path: dongPath,
                selectedLabel: emdName,
                dongId: emdName,
                mapFilter: buildMapFilter(dong, dongPath),
              }
            }
          }
        }
        return {
          path,
          selectedLabel: gu.label,
          mapFilter: buildMapFilter(gu, path),
        }
      }
    }
  }

  const subRegion = extractSubRegion(text, matchedSido)
  if (subRegion) {
    return {
      path,
      selectedLabel: subRegion,
      mapFilter: {
        level: "gu",
        label: subRegion,
        sidoId: matchedSido.id,
        sidoLabel: matchedSido.label,
      },
    }
  }

  return {
    path,
    selectedLabel: matchedSido.label,
    mapFilter: {
      level: "sido",
      label: matchedSido.label,
      sidoId: matchedSido.id,
    },
  }
}
