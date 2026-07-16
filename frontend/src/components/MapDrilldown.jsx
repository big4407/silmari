/**
 * Leaflet 행정구역 드릴다운 지도.
 *
 * [데이터] TopoJSON 시·도/구·군 + admdongkor 동 경계
 * [연동] Dashboard — 지역 클릭 시 mapFilter 변경 → 안내문자 필터
 */
import { useCallback, useEffect, useRef, useState } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import useMapDrilldown from '../hooks/useMapDrilldown';
import { hasDongDrilldown } from '../data/dongRegions';
import { countAlertsForMapRegion } from '../utils/regionMatch';
import {
  getLabelLatLng,
  shouldShowPermanentLabel,
} from '../utils/geoLabelUtils';
import {
  findRegionForFeature,
  getRegionStyle,
  getShortLabel,
  isRegionSelected,
  loadMapGeoJson,
} from '../utils/mapGeoData';
import { getGuLabelFromPath } from '../utils/admDongLoader';
import './MapDrilldown.css';

const KOREA_BOUNDS = L.latLngBounds([33.0, 124.5], [39.0, 132.1]);

const MAP_FIT_ANIMATION = {
  duration: 0.75,
  easeLinearity: 0.22,
};

function stopMapMotion(map) {
  if (map._animatingZoom || map._panAnim?._inProgress) {
    map.stop();
  }
}

function getDisplayLabel(_selected, shortLabel, geoName) {
  const compound = (geoName || '').match(/^(.+시)(.+[구군])$/);
  if (compound) return compound[2];
  return shortLabel;
}

function getFeatureCenter(layer) {
  return layer.getBounds().getCenter();
}

function createLabelIcon(shortLabel, count, isActive, permanent) {
  const countHtml =
    count > 0 ? `<span class="map-region-label__count">${count}</span>` : '';
  return L.divIcon({
    className: '',
    html: `<span class="map-region-label ${isActive ? 'map-region-label--active' : ''} ${count > 0 ? 'map-region-label--has-count' : ''} ${permanent ? '' : 'map-region-label--hover'}"><span class="map-region-label__name">${shortLabel}</span>${countHtml}</span>`,
    iconSize: [0, 0],
    iconAnchor: [0, 0],
  });
}

export default function MapDrilldown({
  onRegionSelect,
  focusTarget,
  alerts = [],
}) {
  const mapRef = useRef(null);
  const mapInstanceRef = useRef(null);
  const geoLayerRef = useRef(null);
  const labelMarkersRef = useRef([]);
  const featureMetaRef = useRef([]);
  const geojsonRef = useRef(null);
  const currentKeyRef = useRef('root');
  const selectedRegionRef = useRef('전국');

  const {
    path,
    currentKey,
    activeGu,
    breadcrumbs,
    selectedRegion,
    selectRegion,
    navigateTo,
    resetMap,
    applyFocus,
  } = useMapDrilldown(onRegionSelect);

  const [geoLoading, setGeoLoading] = useState(false);

  const selectRegionRef = useRef(selectRegion);
  selectRegionRef.current = selectRegion;

  const applyFocusRef = useRef(applyFocus);
  applyFocusRef.current = applyFocus;

  const lastFocusKeyRef = useRef(null);
  const prevCurrentKeyRef = useRef('root');
  const renderGenRef = useRef(0);
  const pathRef = useRef(path);
  const activeGuRef = useRef(activeGu);

  currentKeyRef.current = currentKey;
  selectedRegionRef.current = selectedRegion;
  pathRef.current = path;
  activeGuRef.current = activeGu;

  const clearLabelMarkers = () => {
    labelMarkersRef.current.forEach((m) => m.remove());
    labelMarkersRef.current = [];
  };

  const clearGeoLayer = () => {
    if (geoLayerRef.current) {
      geoLayerRef.current.remove();
      geoLayerRef.current = null;
    }
    featureMetaRef.current = [];
    clearLabelMarkers();
  };

  const updateLayerPresentation = useCallback(
    (map, geojson, key, selected) => {
      clearLabelMarkers();

      featureMetaRef.current.forEach(
        ({
          featureLayer,
          feature,
          region,
          shortLabel,
          labelText,
          geoName,
          alertCount: storedCount,
        }) => {
          const alertCount = region
            ? countAlertsForMapRegion(alerts, region, pathRef.current)
            : storedCount || 0;
          const isActive = isRegionSelected(
            selected,
            region.label,
            geoName,
            shortLabel,
            key,
          );
          const displayLabel = getDisplayLabel(selected, shortLabel, geoName);
          featureLayer.setStyle(getRegionStyle({ isActive, alertCount }));

          const labelLatLng = getLabelLatLng(feature, shortLabel, key);
          const count = alertCount || 0;
          const showPermanent =
            labelLatLng &&
            (isActive ||
              count > 0 ||
              (key !== 'root' &&
                shouldShowPermanentLabel(featureLayer, map, key, {
                  isActive,
                })));

          if (labelLatLng && showPermanent) {
            const labelMarker = L.marker(labelLatLng, {
              icon: createLabelIcon(
                displayLabel,
                alertCount || 0,
                isActive,
                true,
              ),
              interactive: false,
            }).addTo(map);
            labelMarkersRef.current.push(labelMarker);
          }

          const tooltip = featureLayer.getTooltip();
          if (tooltip) {
            const nextLabelText =
              count > 0 ? `${shortLabel} (${count})` : shortLabel;
            tooltip.setContent(nextLabelText);
          }
        },
      );
    },
    [alerts],
  );

  const fitMapToLayer = useCallback((map, layer, key) => {
    if (!layer.getBounds().isValid()) return;
    stopMapMotion(map);
    map.flyToBounds(layer.getBounds(), {
      padding: [12, 12],
      maxZoom: key === 'root' ? 9 : hasDongDrilldown(key) ? 15 : 11,
      ...MAP_FIT_ANIMATION,
    });
  }, []);

  const fitMapToSelection = useCallback((map, selected, key) => {
    if (!selected || selected === '전국') return false;

    const activeLayers = featureMetaRef.current
      .filter(({ region, shortLabel, geoName }) =>
        isRegionSelected(selected, region.label, geoName, shortLabel, key),
      )
      .map(({ featureLayer }) => featureLayer);

    if (activeLayers.length === 0) return false;

    const group = L.featureGroup(activeLayers);
    if (!group.getBounds().isValid()) return false;

    stopMapMotion(map);
    map.flyToBounds(group.getBounds(), {
      padding: [48, 48],
      maxZoom: key === 'root' ? 8 : hasDongDrilldown(key) ? 16 : 13,
      ...MAP_FIT_ANIMATION,
    });
    return true;
  }, []);

  const fitMapView = useCallback(
    (map, layer, key, selected) => {
      if (fitMapToSelection(map, selected, key)) return;
      fitMapToLayer(map, layer, key);
    },
    [fitMapToLayer, fitMapToSelection],
  );

  const handleResetMap = useCallback(() => {
    const wasNationwide =
      currentKeyRef.current === 'root' && selectedRegionRef.current === '전국';
    resetMap();
    if (!wasNationwide) return;
    const map = mapInstanceRef.current;
    const layer = geoLayerRef.current;
    if (!map || !layer) return;
    fitMapView(map, layer, 'root', '전국');
  }, [resetMap, fitMapView]);

  const renderGeoLayer = useCallback(
    async (map) => {
      const key = currentKeyRef.current;
      const gen = ++renderGenRef.current;

      setGeoLoading(true);
      let geojson;
      try {
        const mapPath = pathRef.current;
        const sidoId = mapPath.length >= 2 ? mapPath[1] : null;
        const guLabel =
          activeGuRef.current?.label || getGuLabelFromPath(mapPath);
        geojson = await loadMapGeoJson(key, { sidoId, guLabel });
      } catch (error) {
        console.error('행정동 경계 로드 실패:', error);
        setGeoLoading(false);
        return;
      } finally {
        if (gen === renderGenRef.current) {
          setGeoLoading(false);
        }
      }

      if (
        !mapInstanceRef.current ||
        gen !== renderGenRef.current ||
        currentKeyRef.current !== key
      ) {
        return;
      }

      clearGeoLayer();

      geojsonRef.current = geojson;
      const selected = selectedRegionRef.current;

      const layer = L.geoJSON(geojson, {
        smoothFactor: 0.25,
        style: (feature) => {
          const region = findRegionForFeature(feature, key);
          const geoName = feature.properties?.name || region?.label;
          const shortLabel = getShortLabel(geoName || region?.label || '', key);
          const isActive = region
            ? isRegionSelected(selected, region.label, geoName, shortLabel, key)
            : false;
          const count = region
            ? countAlertsForMapRegion(alerts, region, pathRef.current)
            : 0;
          return getRegionStyle({ isActive, alertCount: count });
        },
        onEachFeature: (feature, featureLayer) => {
          const region = findRegionForFeature(feature, key);
          if (!region) return;

          const geoName = feature.properties?.name || region.label;
          const shortLabel = getShortLabel(geoName || region.label, key);
          const count = countAlertsForMapRegion(
            alerts,
            region,
            pathRef.current,
          );
          const labelText = count > 0 ? `${shortLabel} (${count})` : shortLabel;

          featureMetaRef.current.push({
            featureLayer,
            feature,
            region,
            shortLabel,
            labelText,
            geoName,
            alertCount: count,
          });

          featureLayer.bindTooltip(labelText, {
            permanent: false,
            sticky: true,
            direction: 'top',
            className: `map-region-tooltip${count > 0 ? ' map-region-tooltip--has-count' : ''}`,
            opacity: 1,
          });

          const applyFeatureStyle = () => {
            const active = isRegionSelected(
              selectedRegionRef.current,
              region.label,
              geoName,
              shortLabel,
              key,
            );
            const alertCount = countAlertsForMapRegion(
              alerts,
              region,
              pathRef.current,
            );
            featureLayer.setStyle(
              getRegionStyle({ isActive: active, alertCount }),
            );
          };

          featureLayer.on('mouseover', function () {
            const active = isRegionSelected(
              selectedRegionRef.current,
              region.label,
              geoName,
              shortLabel,
              key,
            );
            if (!active) {
              this.setStyle({
                fillOpacity: 0.82,
                weight: 1.2,
                color: '#94a3b8',
              });
            }
          });
          featureLayer.on('mouseout', applyFeatureStyle);
          featureLayer.on('click', (e) => {
            const target = e.originalEvent?.target;
            if (target && typeof target.blur === 'function') {
              target.blur();
            }
            const center = getFeatureCenter(featureLayer);
            selectRegionRef.current({
              ...region,
              lat: region.lat ?? center.lat,
              lng: region.lng ?? center.lng,
            });
          });
        },
      }).addTo(map);

      if (gen !== renderGenRef.current || currentKeyRef.current !== key) {
        layer.remove();
        return;
      }

      geoLayerRef.current = layer;
      updateLayerPresentation(map, geojson, key, selected);
      fitMapView(map, layer, key, selected);
    },
    [alerts, updateLayerPresentation, fitMapView],
  );

  useEffect(() => {
    if (!mapRef.current || mapInstanceRef.current) return;

    const map = L.map(mapRef.current, {
      center: [36.2, 127.8],
      zoom: 8,
      zoomControl: true,
      maxBounds: KOREA_BOUNDS,
      maxBoundsViscosity: 0.85,
      minZoom: 6,
      maxZoom: 16,
      attributionControl: false,
      preferCanvas: false,
      zoomAnimation: true,
      fadeAnimation: true,
      markerZoomAnimation: true,
      zoomSnap: 0.5,
      zoomDelta: 0.5,
      zoomAnimationThreshold: 10,
      wheelPxPerZoomLevel: 55,
      inertia: true,
      easeLinearity: 0.2,
    });

    mapInstanceRef.current = map;
    renderGeoLayer(map);

    return () => {
      map.remove();
      mapInstanceRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    const map = mapInstanceRef.current;
    if (!map) return;
    renderGeoLayer(map);
  }, [currentKey, activeGu, renderGeoLayer]);

  useEffect(() => {
    const map = mapInstanceRef.current;
    const geojson = geojsonRef.current;
    if (!map || !geoLayerRef.current || !geojson) return;
    updateLayerPresentation(map, geojson, currentKey, selectedRegion);
  }, [selectedRegion, currentKey, alerts, updateLayerPresentation]);

  useEffect(() => {
    const keyChanged = prevCurrentKeyRef.current !== currentKey;
    prevCurrentKeyRef.current = currentKey;
    if (keyChanged) return;

    const map = mapInstanceRef.current;
    const layer = geoLayerRef.current;
    if (!map || !layer) return;
    fitMapView(map, layer, currentKey, selectedRegion);
  }, [selectedRegion, currentKey, fitMapView]);

  useEffect(() => {
    if (!focusTarget?.key) return;
    if (lastFocusKeyRef.current === focusTarget.key) return;
    lastFocusKeyRef.current = focusTarget.key;
    applyFocusRef.current(focusTarget);
  }, [focusTarget?.key]);

  useEffect(() => {
    const map = mapInstanceRef.current;
    if (!map || !mapRef.current) return;

    let resizeRaf = null;
    const observer = new ResizeObserver(() => {
      if (resizeRaf) cancelAnimationFrame(resizeRaf);
      resizeRaf = requestAnimationFrame(() => {
        resizeRaf = null;
        if (!map._animatingZoom) {
          map.invalidateSize({ animate: false });
        }
      });
    });
    observer.observe(mapRef.current);
    return () => observer.disconnect();
  }, []);

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
                  <button type="button" onClick={() => navigateTo(i)}>
                    {crumb.label}
                  </button>
                ) : (
                  <strong>{crumb.label}</strong>
                )}
              </span>
            ))}
          </div>
          <button
            type="button"
            className="map-reset-btn"
            onClick={handleResetMap}
          >
            전국 보기
          </button>
        </div>
      </div>
      <div className="map-body">
        {geoLoading && <div className="map-loading">행정구역 불러오는 중…</div>}
        <div ref={mapRef} className="leaflet-map" />
      </div>
    </div>
  );
}
