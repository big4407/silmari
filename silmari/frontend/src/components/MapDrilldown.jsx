import { useEffect, useRef } from "react"
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
  loadMapGeoJson,
} from "../utils/mapGeoData"
import "./MapDrilldown.css"

const KOREA_BOUNDS = L.latLngBounds([33.0, 124.5], [39.0, 132.1])

function getFeatureCenter(layer) {
  return layer.getBounds().getCenter()
}

function createLabelIcon(text, isActive, permanent) {
  return L.divIcon({
    className: "",
    html: `<span class="map-region-label ${isActive ? "map-region-label--active" : ""} ${permanent ? "" : "map-region-label--hover"}">${text}</span>`,
    iconSize: [0, 0],
    iconAnchor: [0, 0],
  })
}

export default function MapDrilldown({ onRegionSelect, focusTarget, alerts = [] }) {
  const mapRef = useRef(null)
  const mapInstanceRef = useRef(null)
  const geoLayerRef = useRef(null)
  const labelMarkersRef = useRef([])

  const {
    currentKey,
    breadcrumbs,
    selectedRegion,
    selectRegion,
    navigateTo,
    resetMap,
    applyFocus,
  } = useMapDrilldown(onRegionSelect)

  const clearLabelMarkers = () => {
    labelMarkersRef.current.forEach(m => m.remove())
    labelMarkersRef.current = []
  }

  const clearGeoLayer = () => {
    if (geoLayerRef.current) {
      geoLayerRef.current.remove()
      geoLayerRef.current = null
    }
    clearLabelMarkers()
  }

  const renderGeoLayer = async (map) => {
    clearGeoLayer()

    let geojson
    try {
      geojson = await loadMapGeoJson(currentKey)
    } catch {
      return
    }

    if (!mapInstanceRef.current) return

    const layer = L.geoJSON(geojson, {
      smoothFactor: 0.25,
      style: (feature) => {
        const region = findRegionForFeature(feature, currentKey)
        const label = region?.label || feature.properties?.name
        const isActive = selectedRegion === label
          || selectedRegion === getShortLabel(feature.properties?.name, currentKey)
        const idx = geojson.features.indexOf(feature)
        return getRegionStyle({ isActive, colorIndex: idx })
      },
      onEachFeature: (feature, featureLayer) => {
        const region = findRegionForFeature(feature, currentKey)
        if (!region) return

        const shortLabel = getShortLabel(feature.properties?.name || region.label, currentKey)
        const count = currentKey === "root" ? countAlertsForSido(alerts, region.label) : 0
        const labelText = count > 0 ? `${shortLabel} (${count})` : shortLabel
        const isActive = selectedRegion === region.label || selectedRegion === shortLabel
        const labelLatLng = getLabelLatLng(feature, shortLabel, currentKey)
        const showPermanent = labelLatLng
          ? shouldShowPermanentLabel(featureLayer, map, currentKey)
          : false

        if (labelLatLng) {
          const labelMarker = L.marker(labelLatLng, {
            icon: createLabelIcon(labelText, isActive, showPermanent),
            interactive: false,
          })
          if (showPermanent) {
            labelMarker.addTo(map)
            labelMarkersRef.current.push(labelMarker)
          }
        }

        featureLayer.bindTooltip(labelText, {
          permanent: false,
          sticky: true,
          direction: "top",
          className: `map-region-tooltip ${isActive ? "map-region-tooltip--active" : ""}`,
          opacity: 1,
        })

        featureLayer.on("mouseover", function () {
          if (!isActive) {
            this.setStyle({ fillOpacity: 0.82, weight: 1.2, color: "#94a3b8" })
          }
        })
        featureLayer.on("mouseout", function () {
          layer.resetStyle(this)
        })
        featureLayer.on("click", () => {
          const center = getFeatureCenter(featureLayer)
          selectRegion({
            ...region,
            lat: region.lat ?? center.lat,
            lng: region.lng ?? center.lng,
          })
        })
      },
    }).addTo(map)

    geoLayerRef.current = layer

    if (layer.getBounds().isValid()) {
      map.fitBounds(layer.getBounds(), { padding: [24, 24], maxZoom: currentKey === "root" ? 8 : 12 })
    }
  }

  useEffect(() => {
    if (!mapRef.current || mapInstanceRef.current) return

    const map = L.map(mapRef.current, {
      center: [36.2, 127.8],
      zoom: 7,
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
  }, [])

  useEffect(() => {
    const map = mapInstanceRef.current
    if (!map) return
    renderGeoLayer(map)
  }, [currentKey, selectedRegion, alerts])

  useEffect(() => {
    if (!focusTarget) return
    applyFocus(focusTarget)
    const map = mapInstanceRef.current
    if (map && focusTarget.center) {
      map.flyTo(focusTarget.center, focusTarget.zoom || 11, { duration: 0.8 })
    }
  }, [focusTarget])

  return (
    <div className="map-container">
      <div className="map-header">
        <h2>지도</h2>
        <div className="map-header__controls">
          <div className="map-breadcrumb">
            {breadcrumbs.map((crumb, i) => (
              <span key={crumb.key}>
                {i > 0 && <span> › </span>}
                {i < breadcrumbs.length - 1 ? (
                  <button onClick={() => navigateTo(i)}>{crumb.label}</button>
                ) : (
                  <strong>{crumb.label}</strong>
                )}
              </span>
            ))}
          </div>
          <button className="map-reset-btn" onClick={resetMap}>전국 보기</button>
        </div>
      </div>
      <div className="map-body">
        <div ref={mapRef} className="leaflet-map" />
      </div>
    </div>
  )
}
