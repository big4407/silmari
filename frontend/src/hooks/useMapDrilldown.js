import { useState, useCallback, useMemo, useRef } from "react"
import { buildMapFilter } from "../utils/regionMatch"

export const REGION_DATA = {
  root: {
    label: "전국",
    center: [36.2, 127.8],
    zoom: 7,
    regions: [
      { id: "11", label: "서울", lat: 37.5665, lng: 126.978 },
      { id: "26", label: "부산", lat: 35.1796, lng: 129.0756 },
      { id: "27", label: "대구", lat: 35.8714, lng: 128.6014 },
      { id: "28", label: "인천", lat: 37.4563, lng: 126.7052 },
      { id: "29", label: "광주", lat: 35.1595, lng: 126.8526 },
      { id: "30", label: "대전", lat: 36.3504, lng: 127.3845 },
      { id: "36", label: "세종", lat: 36.48, lng: 127.289 },
      { id: "31", label: "울산", lat: 35.5384, lng: 129.3114 },
      { id: "41", label: "경기", lat: 37.4138, lng: 127.5183 },
      { id: "42", label: "강원", lat: 37.8228, lng: 128.1555 },
      { id: "43", label: "충북", lat: 36.6357, lng: 127.4917 },
      { id: "44", label: "충남", lat: 36.5184, lng: 126.8 },
      { id: "45", label: "전북", lat: 35.7175, lng: 127.153 },
      { id: "46", label: "전남", lat: 34.8679, lng: 126.991 },
      { id: "47", label: "경북", lat: 36.4919, lng: 128.8889 },
      { id: "48", label: "경남", lat: 35.4606, lng: 128.2132 },
      { id: "50", label: "제주", lat: 33.4996, lng: 126.5312 },
    ],
  },
  "11": {
    label: "서울",
    center: [37.5665, 126.978],
    zoom: 11,
    regions: [
      { id: "1100", label: "종로구", lat: 37.5729, lng: 126.9794 },
      { id: "1101", label: "중구", lat: 37.5641, lng: 126.9970 },
      { id: "1102", label: "용산구", lat: 37.5324, lng: 126.9900 },
      { id: "1103", label: "성동구", lat: 37.5633, lng: 127.0366 },
      { id: "1104", label: "광진구", lat: 37.5384, lng: 127.0822 },
      { id: "1105", label: "동대문구", lat: 37.5744, lng: 127.0396 },
      { id: "1106", label: "중랑구", lat: 37.6063, lng: 127.0928 },
      { id: "1107", label: "성북구", lat: 37.5891, lng: 127.0167 },
      { id: "1108", label: "강북구", lat: 37.6396, lng: 127.0255 },
      { id: "1109", label: "도봉구", lat: 37.6687, lng: 127.0471 },
      { id: "1110", label: "노원구", lat: 37.6542, lng: 127.0568 },
      { id: "1111", label: "은평구", lat: 37.6026, lng: 126.9291 },
      { id: "1112", label: "서대문구", lat: 37.5791, lng: 126.9368 },
      { id: "1113", label: "마포구", lat: 37.5663, lng: 126.9019 },
      { id: "1114", label: "양천구", lat: 37.5169, lng: 126.8665 },
      { id: "1115", label: "강서구", lat: 37.5509, lng: 126.8495 },
      { id: "1116", label: "구로구", lat: 37.4954, lng: 126.8874 },
      { id: "1117", label: "금천구", lat: 37.4519, lng: 126.9019 },
      { id: "1118", label: "영등포구", lat: 37.5264, lng: 126.8962 },
      { id: "1119", label: "동작구", lat: 37.5124, lng: 126.9393 },
      { id: "1120", label: "관악구", lat: 37.4781, lng: 126.9515 },
      { id: "1121", label: "서초구", lat: 37.4837, lng: 127.0324 },
      { id: "1122", label: "강남구", lat: 37.5172, lng: 127.0473 },
      { id: "1123", label: "송파구", lat: 37.5145, lng: 127.1059 },
      { id: "1124", label: "강동구", lat: 37.5301, lng: 127.1238 },
    ],
  },
  "26": {
    label: "부산",
    center: [35.1796, 129.0756],
    zoom: 11,
    regions: [
      { id: "2600", label: "중구", lat: 35.106, lng: 129.0324 },
      { id: "2601", label: "서구", lat: 35.0979, lng: 129.0244 },
      { id: "2602", label: "동구", lat: 35.1297, lng: 129.0454 },
      { id: "2603", label: "영도구", lat: 35.0912, lng: 129.0679 },
      { id: "2604", label: "부산진구", lat: 35.1629, lng: 129.0532 },
      { id: "2605", label: "동래구", lat: 35.2045, lng: 129.0780 },
      { id: "2606", label: "남구", lat: 35.1366, lng: 129.0847 },
      { id: "2607", label: "북구", lat: 35.197, lng: 128.9915 },
      { id: "2608", label: "해운대구", lat: 35.1631, lng: 129.1635 },
      { id: "2609", label: "사하구", lat: 35.1047, lng: 128.9743 },
      { id: "2610", label: "금정구", lat: 35.2429, lng: 129.0921 },
      { id: "2611", label: "강서구", lat: 35.2124, lng: 128.9805 },
      { id: "2612", label: "연제구", lat: 35.1763, lng: 129.0799 },
      { id: "2613", label: "수영구", lat: 35.1456, lng: 129.1130 },
      { id: "2614", label: "사상구", lat: 35.1527, lng: 128.9910 },
      { id: "2615", label: "기장군", lat: 35.2446, lng: 129.2223 },
    ],
  },
  "36": {
    label: "세종",
    center: [36.48, 127.289],
    zoom: 11,
    regions: [
      { id: "36010", label: "세종시", lat: 36.48, lng: 127.289 },
    ],
  },
}

const SIDO_ONLY_ZOOM = 9
const GU_ZOOM = 13

export default function useMapDrilldown(onRegionSelect) {
  const [path, setPath] = useState(["root"])
  const [selectedRegion, setSelectedRegion] = useState("전국")
  const [sidoFocus, setSidoFocus] = useState(null)
  const [guFocus, setGuFocus] = useState(null)

  const onRegionSelectRef = useRef(onRegionSelect)
  onRegionSelectRef.current = onRegionSelect

  const currentKey = path[path.length - 1]
  const drillData = REGION_DATA[currentKey] || REGION_DATA.root

  const mapView = useMemo(() => {
    if (guFocus) {
      return { center: [guFocus.lat, guFocus.lng], zoom: GU_ZOOM }
    }
    if (sidoFocus) {
      return { center: [sidoFocus.lat, sidoFocus.lng], zoom: SIDO_ONLY_ZOOM }
    }
    return { center: drillData.center, zoom: drillData.zoom }
  }, [guFocus, sidoFocus, drillData])

  const displayRegions = drillData.regions

  const breadcrumbs = useMemo(() => {
    const crumbs = path.map(key => ({
      key,
      label: key === "root"
        ? "전국"
        : (REGION_DATA[key]?.label
          || REGION_DATA.root.regions.find(r => r.id === key)?.label
          || key),
    }))
    if (guFocus && path.length > 1) {
      crumbs.push({ key: `gu-${guFocus.id}`, label: guFocus.label })
    } else if (sidoFocus && path.length === 1) {
      crumbs.push({ key: `sido-${sidoFocus.id}`, label: sidoFocus.label })
    }
    return crumbs
  }, [path, sidoFocus, guFocus])

  const applyFocus = useCallback((focus) => {
    if (!focus?.path) return
    setSidoFocus(null)
    setGuFocus(null)
    setPath(focus.path)
    setSelectedRegion(focus.selectedLabel || "전국")

    if (focus.mapFilter) {
      onRegionSelectRef.current?.(focus.mapFilter)
      if (focus.path.length > 1) {
        const sidoId = focus.path[1]
        const gu = REGION_DATA[sidoId]?.regions?.find(r => r.label === focus.selectedLabel)
        if (gu) {
          setGuFocus(gu)
        } else if (focus.mapFilter.level === "gu") {
          setGuFocus({
            id: `geo-${focus.selectedLabel}`,
            label: focus.selectedLabel,
            lat: null,
            lng: null,
          })
        }
      }
      return
    }

    const lastKey = focus.path[focus.path.length - 1]
    if (lastKey === "root") {
      onRegionSelectRef.current?.({ level: "nation" })
      return
    }

    const sidoId = focus.path[1]
    const gu = REGION_DATA[sidoId]?.regions?.find(r => r.label === focus.selectedLabel)
    if (gu) {
      setGuFocus(gu)
      onRegionSelectRef.current?.(buildMapFilter(gu, focus.path))
      return
    }

    const sido = REGION_DATA.root.regions.find(r => r.id === sidoId)
    if (sido) onRegionSelectRef.current?.(buildMapFilter(sido, focus.path))
  }, [])

  const selectRegion = useCallback((region) => {
    const isSido = REGION_DATA.root.regions.some(r => r.id === region.id)
    const inSidoView = path.length > 1

    if (path.length === 1 && isSido) {
      setSidoFocus(null)
      setGuFocus(null)
      const nextPath = [...path, region.id]
      setPath(nextPath)
      setSelectedRegion(region.label)
      onRegionSelectRef.current?.(buildMapFilter(region, nextPath))
      return
    }

    if (inSidoView) {
      setSidoFocus(null)
      setGuFocus(region)
      setSelectedRegion(region.label)
      onRegionSelectRef.current?.(buildMapFilter(region, path))
      return
    }

    if (isSido) {
      setPath(["root"])
      setSidoFocus(region)
      setGuFocus(null)
      setSelectedRegion(region.label)
      onRegionSelectRef.current?.(buildMapFilter(region, ["root", region.id]))
    }
  }, [path])

  const navigateTo = useCallback((index) => {
    const crumb = breadcrumbs[index]
    if (!crumb) return

    if (crumb.key === "root") {
      setPath(["root"])
      setSidoFocus(null)
      setGuFocus(null)
      setSelectedRegion("전국")
      onRegionSelectRef.current?.({ level: "nation" })
      return
    }

    if (crumb.key.startsWith("sido-")) {
      const sido = REGION_DATA.root.regions.find(r => r.id === crumb.key.replace("sido-", ""))
      if (!sido) return
      setPath(["root"])
      setSidoFocus(sido)
      setGuFocus(null)
      setSelectedRegion(sido.label)
      onRegionSelectRef.current?.(buildMapFilter(sido, ["root", sido.id]))
      return
    }

    if (crumb.key.startsWith("gu-")) {
      const gu = REGION_DATA[path[1]]?.regions?.find(r => r.id === crumb.key.replace("gu-", ""))
      if (!gu) return
      setGuFocus(gu)
      setSelectedRegion(gu.label)
      onRegionSelectRef.current?.(buildMapFilter(gu, path))
      return
    }

    const keyIndex = path.indexOf(crumb.key)
    if (keyIndex < 0) return
    const newPath = path.slice(0, keyIndex + 1)
    setPath(newPath)
    setSidoFocus(null)
    setGuFocus(null)
    const label = REGION_DATA[crumb.key]?.label || crumb.label
    setSelectedRegion(label)
    const sido = REGION_DATA.root.regions.find(r => r.id === crumb.key)
    onRegionSelectRef.current?.(sido ? buildMapFilter(sido, newPath) : { level: "nation" })
  }, [path, breadcrumbs])

  const resetMap = useCallback(() => {
    setPath(["root"])
    setSidoFocus(null)
    setGuFocus(null)
    setSelectedRegion("전국")
    onRegionSelectRef.current?.({ level: "nation" })
  }, [])

  return {
    path,
    currentKey,
    mapView,
    displayRegions,
    breadcrumbs,
    selectedRegion,
    selectRegion,
    navigateTo,
    resetMap,
    applyFocus,
  }
}
