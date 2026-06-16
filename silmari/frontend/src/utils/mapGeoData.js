import * as topojson from "topojson-client"
import { REGION_DATA } from "../hooks/useMapDrilldown"
import { SIDO_SEARCH_TERMS } from "./regionMatch"

/** REGION_DATA 행정코드 → southkorea-maps GeoJSON 시도코드 */
export const GEO_SIDO_CODE_MAP = {
  11: "11",
  26: "21",
  27: "22",
  28: "23",
  29: "24",
  30: "25",
  36: "29",
  31: "26",
  41: "31",
  42: "32",
  43: "33",
  44: "34",
  45: "35",
  46: "36",
  47: "37",
  48: "38",
  50: "39",
}

const REGION_COLORS = [
  "#dbeafe", "#e0f2fe", "#dcfce7", "#fef3c7", "#ede9fe",
  "#fce7f3", "#ccfbf1", "#ffedd5", "#ecfccb", "#f3e8ff",
  "#fee2e2", "#e0e7ff", "#d1fae5", "#fde68a", "#fae8ff",
  "#bfdbfe", "#fecdd3",
]

let municipalitiesCache = null

async function loadTopoCollection(topoFile, objectName) {
  const res = await fetch(topoFile)
  const topology = await res.json()
  return topojson.feature(topology, topology.objects[objectName])
}

async function loadMunicipalities() {
  if (!municipalitiesCache) {
    municipalitiesCache = await loadTopoCollection(
      "/geodata/municipalities.topo.json",
      "skorea_municipalities_geo",
    )
  }
  return municipalitiesCache
}

export async function loadMapGeoJson(currentKey) {
  if (currentKey === "root") {
    return loadTopoCollection("/geodata/korea.topo.json", "skorea_provinces_geo")
  }

  const geoSido = GEO_SIDO_CODE_MAP[currentKey]
  if (!geoSido) {
    return { type: "FeatureCollection", features: [] }
  }

  const data = await loadMunicipalities()
  return {
    type: "FeatureCollection",
    features: data.features.filter(f =>
      String(f.properties?.code || "").startsWith(geoSido),
    ),
  }
}

export function getRegionColor(index) {
  return REGION_COLORS[index % REGION_COLORS.length]
}

export function getRegionStyle({ isActive, colorIndex }) {
  return {
    fillColor: isActive ? "#fb923c" : getRegionColor(colorIndex),
    fillOpacity: isActive ? 0.85 : 0.62,
    color: isActive ? "#ea580c" : "#cbd5e1",
    weight: isActive ? 2 : 0.7,
  }
}

function matchSidoRegion(geoName) {
  for (const region of REGION_DATA.root.regions) {
    const terms = SIDO_SEARCH_TERMS[region.label] || [region.label]
    if (terms.some(term => geoName.includes(term))) {
      return region
    }
  }
  return null
}

function matchGuRegion(geoName, sidoKey) {
  const regions = REGION_DATA[sidoKey]?.regions
  if (!regions) return null
  return regions.find(r => geoName.includes(r.label) || r.label === geoName) || null
}

export function findRegionForFeature(feature, currentKey) {
  const geoName = feature.properties?.name || feature.properties?.SIG_KOR_NM || ""

  if (currentKey === "root") {
    return matchSidoRegion(geoName)
  }

  const matched = matchGuRegion(geoName, currentKey)
  if (matched) return matched

  return {
    id: String(feature.properties?.code || geoName),
    label: geoName,
    lat: null,
    lng: null,
  }
}

export function getShortLabel(name, currentKey) {
  if (currentKey === "root") {
    for (const region of REGION_DATA.root.regions) {
      const terms = SIDO_SEARCH_TERMS[region.label] || [region.label]
      if (terms.some(term => name.includes(term))) {
        return region.label
      }
    }
    return name.replace(/특별자치시|특별자치도|광역시|특별시|도$/g, "")
  }
  const cleaned = name.replace(/\(.*\)/, "").trim()
  const compound = cleaned.match(/^(.+시)(.+[구군])$/)
  if (compound) return compound[2]
  return cleaned
}

/** 선택된 지역과 GeoJSON feature 매칭 (성남시 ↔ 성남시분당구 등) */
export function isRegionSelected(selectedRegion, regionLabel, geoName, shortLabel) {
  if (!selectedRegion || selectedRegion === "전국") return false
  if (selectedRegion === regionLabel || selectedRegion === shortLabel) return true

  const sel = selectedRegion.replace(/\s/g, "")
  const geo = (geoName || "").replace(/\s/g, "")
  if (!geo || !sel) return false

  if (geo.includes(sel) || sel.includes(geo)) return true

  const cityGu = sel.match(/^(.+시)(.+[구군])$/)
  if (cityGu && geo.includes(cityGu[1]) && geo.includes(cityGu[2])) return true

  const cityOnly = sel.match(/^(.+시)$/)
  if (cityOnly && geo.startsWith(cityOnly[1])) return true

  return false
}
