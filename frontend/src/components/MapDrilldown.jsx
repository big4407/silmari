import { useCallback, useEffect, useRef } from "react"
import L from "leaflet"
import "leaflet/dist/leaflet.css"
import useMapDrilldown from "../hooks/useMapDrilldown"
import { countAlertsForSido } from "../utils/regionMatch"
import {
  getLabelLatLng,
  shouldShowPermanentLabel,
} from "../utils/geoLabelUtils"
import {
  findRegionForFeature,
  getRegionStyle,
  getShortLabel,
  isRegionSelected,
  loadMapGeoJson,
} from "../utils/mapGeoData"
import "./MapDrilldown.css"

const KOREA_BOUNDS = L.latLngBounds([33.0, 124.5], [39.0, 132.1])

function getDisplayLabel(_selected, shortLabel, geoName) {
  const compound = (geoName || "").match(/^(.+시)(.+[구군])$/)
  if (compound) return compound[2]
  return shortLabel
}

function getFeatureCenter(layer) {
  return layer.getBounds().getCenter()
}

function createLabelIcon(shortLabel, count, isActive, permanent) {
  const countHtml = count > 0
    ? `<span class="map-region-label__count">${count}</span>`
    : ""
  return L.divIcon({
    className: "",
    html: `<span class="map-region-label ${isActive ? "map-region-label--active" : ""} ${count > 0 ? "map-region-label--has-count" : ""} ${permanent ? "" : "map-region-label--hover"}"><span class="map-region-label__name">${shortLabel}</span>${countHtml}</span>`,
    iconSize: [0, 0],
    iconAnchor: [0, 0],
  })
}

const FIT_OPTIONS = { duration: 0.35 }

export default function MapDrilldown({ onRegionSelect, focusTarget, alerts = [] }) {
  const mapRef = useRef(null)
  const mapInstanceRef = useRef(null)
  const geoLayerRef = useRef(null)
  const labelMarkerMapRef = useRef(new Map())
  const featureMetaRef = useRef([])
  const geojsonRef = useRef(null)
  const alertsRef = useRef(alerts)
  const currentKeyRef = useRef("root")
  const selectedRegionRef = useRef("전국")

  alertsRef.current = alerts

  const {
    currentKey,
    breadcrumbs,
    selectedRegion,
    selectRegion,
    navigateTo,
    resetMap,
    applyFocus,
  } = useMapDrilldown(onRegionSelect)

  const selectRegionRef = useRef(selectRegion)
  selectRegionRef.current = selectRegion

  const applyFocusRef = useRef(applyFocus)
  applyFocusRef.current = applyFocus

  const lastFocusKeyRef = useRef(null)
  const prevCurrentKeyRef = useRef("root")

  currentKeyRef.current = currentKey
  selectedRegionRef.current = selectedRegion

  const clearLabelMarkers = () => {
    labelMarkerMapRef.current.forEach(m => m.remove())
    labelMarkerMapRef.current.clear()
  }

  const clearGeoLayer = () => {
    if (geoLayerRef.current) {
      geoLayerRef.current.remove()
      geoLayerRef.current = null
    }
    featureMetaRef.current = []
    clearLabelMarkers()
  }

  const applyFeatureStyle = useCallback((featureLayer, meta, selected) => {
    const { region, shortLabel, geoName, colorIndex, alertCount } = meta
    const isActive = isRegionSelected(selected, region.label, geoName, shortLabel)
    featureLayer.setStyle(getRegionStyle({ isActive, colorIndex, alertCount }))
  }, [])

  const updateLayerPresentation = useCallback((map, geojson, key, selected) => {
    const visibleLabelIds = new Set()

    featureMetaRef.current.forEach((meta) => {
      const { featureLayer, feature, region, shortLabel, geoName, alertCount } = meta
      const isActive = isRegionSelected(selected, region.label, geoName, shortLabel)
      const displayLabel = getDisplayLabel(selected, shortLabel, geoName)
      applyFeatureStyle(featureLayer, meta, selected)

      const labelLatLng = getLabelLatLng(feature, shortLabel, key)
      const count = alertCount || 0
      const showPermanent = labelLatLng && (
        isActive
        || count > 0
        || (key !== "root" && shouldShowPermanentLabel(featureLayer, map, key, { isActive }))
      )

      if (labelLatLng && showPermanent) {
        visibleLabelIds.add(region.id)
        const icon = createLabelIcon(displayLabel, count, isActive, true)
        const existing = labelMarkerMapRef.current.get(region.id)
        if (existing) {
          existing.setLatLng(labelLatLng)
          existing.setIcon(icon)
        } else {
          labelMarkerMapRef.current.set(
            region.id,
            L.marker(labelLatLng, { icon, interactive: false }).addTo(map),
          )
        }
      }

      const tooltip = featureLayer.getTooltip()
      if (tooltip) {
        tooltip.setContent(meta.labelText)
      }
    })

    labelMarkerMapRef.current.forEach((marker, id) => {
      if (!visibleLabelIds.has(id)) {
        marker.remove()
        labelMarkerMapRef.current.delete(id)
      }
    })
  }, [applyFeatureStyle])

  const syncAlertCounts = useCallback((key) => {
    if (key !== "root") return
    featureMetaRef.current.forEach((meta) => {
      const count = countAlertsForSido(alertsRef.current, meta.region.label)
      meta.alertCount = count
      meta.labelText = count > 0 ? `${meta.shortLabel} (${count})` : meta.shortLabel
    })
  }, [])

  const fitMapToLayer = useCallback((map, layer, key) => {
    if (!layer.getBounds().isValid()) return
    map.fitBounds(layer.getBounds(), {
      padding: [8, 8],
      maxZoom: key === "root" ? 9 : 11,
      animate: true,
      ...FIT_OPTIONS,
    })
    requestAnimationFrame(() => map.invalidateSize())
  }, [])

  const fitMapToSelection = useCallback((map, selected, key) => {
    if (!selected || selected === "전국") return false

    const activeLayers = featureMetaRef.current
      .filter(({ region, shortLabel, geoName }) =>
        isRegionSelected(selected, region.label, geoName, shortLabel),
      )
      .map(({ featureLayer }) => featureLayer)

    if (activeLayers.length === 0) return false

    const group = L.featureGroup(activeLayers)
    if (!group.getBounds().isValid()) return false

    map.fitBounds(group.getBounds(), {
      padding: [48, 48],
      maxZoom: key === "root" ? 8 : 13,
      animate: true,
      ...FIT_OPTIONS,
    })
    requestAnimationFrame(() => map.invalidateSize())
    return true
  }, [])

  const fitMapView = useCallback((map, layer, key, selected) => {
    if (fitMapToSelection(map, selected, key)) return
    fitMapToLayer(map, layer, key)
  }, [fitMapToLayer, fitMapToSelection])

  const handleResetMap = useCallback(() => {
    const wasNationwide =
      currentKeyRef.current === "root" && selectedRegionRef.current === "전국"
    resetMap()
    if (!wasNationwide) return
    const map = mapInstanceRef.current
    const layer = geoLayerRef.current
    if (!map || !layer) return
    fitMapView(map, layer, "root", "전국")
  }, [resetMap, fitMapView])

  const renderGeoLayer = useCallback(async (map) => {
    clearGeoLayer()

    const key = currentKeyRef.current
    let geojson
    try {
      geojson = await loadMapGeoJson(key)
    } catch {
      return
    }

    if (!mapInstanceRef.current || currentKeyRef.current !== key) return

    geojsonRef.current = geojson
    const selected = selectedRegionRef.current

    const layer = L.geoJSON(geojson, {
      smoothFactor: 0.5,
      style: (feature) => {
        const region = findRegionForFeature(feature, key)
        const geoName = feature.properties?.name || region?.label
        const shortLabel = getShortLabel(geoName || region?.label || "", key)
        const isActive = region
          ? isRegionSelected(selected, region.label, geoName, shortLabel)
          : false
        const idx = geojson.features.indexOf(feature)
        const count = key === "root" && region
          ? countAlertsForSido(alertsRef.current, region.label)
          : 0
        return getRegionStyle({ isActive, colorIndex: idx, alertCount: count })
      },
      onEachFeature: (feature, featureLayer) => {
        const region = findRegionForFeature(feature, key)
        if (!region) return

        const geoName = feature.properties?.name || region.label
        const shortLabel = getShortLabel(geoName || region.label, key)
        const colorIndex = geojson.features.indexOf(feature)
        const count = key === "root" ? countAlertsForSido(alertsRef.current, region.label) : 0
        const labelText = count > 0 ? `${shortLabel} (${count})` : shortLabel

        const meta = {
          featureLayer,
          feature,
          region,
          shortLabel,
          labelText,
          geoName,
          alertCount: count,
          colorIndex,
        }
        featureMetaRef.current.push(meta)

        featureLayer.bindTooltip(labelText, {
          permanent: false,
          sticky: true,
          direction: "top",
          className: `map-region-tooltip${count > 0 ? " map-region-tooltip--has-count" : ""}`,
          opacity: 1,
        })

        featureLayer.on("mouseover", function () {
          const active = isRegionSelected(
            selectedRegionRef.current,
            region.label,
            geoName,
            shortLabel,
          )
          if (!active) {
            this.setStyle({ fillOpacity: 0.82, weight: 1.2, color: "#94a3b8" })
          }
        })
        featureLayer.on("mouseout", function () {
          const entry = featureMetaRef.current.find(m => m.featureLayer === this)
          if (!entry) {
            layer.resetStyle(this)
            return
          }
          applyFeatureStyle(this, entry, selectedRegionRef.current)
        })
        featureLayer.on("click", () => {
          const center = getFeatureCenter(featureLayer)
          selectRegionRef.current({
            ...region,
            lat: region.lat ?? center.lat,
            lng: region.lng ?? center.lng,
          })
        })
      },
    }).addTo(map)

    geoLayerRef.current = layer
    updateLayerPresentation(map, geojson, key, selected)
    fitMapView(map, layer, key, selected)
  }, [updateLayerPresentation, fitMapView, applyFeatureStyle])

  useEffect(() => {
    if (!mapRef.current || mapInstanceRef.current) return

    const map = L.map(mapRef.current, {
      center: [36.2, 127.8],
      zoom: 8,
      zoomControl: true,
      maxBounds: KOREA_BOUNDS,
      maxBoundsViscosity: 1.0,
      minZoom: 6,
      attributionControl: false,
      preferCanvas: true,
    })

    mapInstanceRef.current = map
    renderGeoLayer(map)

    return () => {
      map.remove()
      mapInstanceRef.current = null
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    const map = mapInstanceRef.current
    if (!map) return
    renderGeoLayer(map)
  }, [currentKey, renderGeoLayer])

  useEffect(() => {
    const map = mapInstanceRef.current
    const geojson = geojsonRef.current
    if (!map || !geoLayerRef.current || !geojson) return
    syncAlertCounts(currentKey)
    updateLayerPresentation(map, geojson, currentKey, selectedRegion)
  }, [alerts, selectedRegion, currentKey, syncAlertCounts, updateLayerPresentation])

  useEffect(() => {
    const keyChanged = prevCurrentKeyRef.current !== currentKey
    prevCurrentKeyRef.current = currentKey
    if (keyChanged) return

    const map = mapInstanceRef.current
    const layer = geoLayerRef.current
    if (!map || !layer) return
    fitMapView(map, layer, currentKey, selectedRegion)
  }, [selectedRegion, currentKey, fitMapView])

  useEffect(() => {
    if (!focusTarget?.key) return
    if (lastFocusKeyRef.current === focusTarget.key) return
    lastFocusKeyRef.current = focusTarget.key
    applyFocusRef.current(focusTarget)
  }, [focusTarget?.key])

  useEffect(() => {
    const map = mapInstanceRef.current
    if (!map || !mapRef.current) return

    const observer = new ResizeObserver(() => {
      map.invalidateSize()
    })
    observer.observe(mapRef.current)
    return () => observer.disconnect()
  }, [])

  return (
    <div className="map-container">
      <div className="map-header">
        <span className="map-header__title">지역 지도</span>
        <div className="map-header__controls">
          <div className="map-breadcrumb">
            {breadcrumbs.map((crumb, i) => (
              <span key={crumb.key}>
                {i > 0 && <span className="map-breadcrumb__sep"> › </span>}
                {i < breadcrumbs.length - 1 ? (
                  <button type="button" onClick={() => navigateTo(i)}>{crumb.label}</button>
                ) : (
                  <strong>{crumb.label}</strong>
                )}
              </span>
            ))}
          </div>
          <button type="button" className="map-reset-btn" onClick={handleResetMap}>전국 보기</button>
        </div>
      </div>
      <div className="map-body">
        <div ref={mapRef} className="leaflet-map" />
      </div>
    </div>
  )
}
