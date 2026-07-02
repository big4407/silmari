/** 시·도 라벨 수동 좌표 (바다/섬 지역 바운딩박스 중심 보정) */
import { hasDongDrilldown } from '../data/dongRegions';
export const SIDO_LABEL_POSITIONS = {
  서울: [37.5665, 126.978],
  부산: [35.18, 129.05],
  대구: [35.87, 128.55],
  인천: [37.48, 126.68],
  광주: [35.16, 126.85],
  대전: [36.35, 127.38],
  세종: [36.48, 127.29],
  울산: [35.54, 129.25],
  경기: [37.75, 127.15],
  강원: [37.75, 128.35],
  충북: [36.78, 127.85],
  충남: [36.55, 126.85],
  전북: [35.75, 127.25],
  전남: [34.95, 126.75],
  경북: [36.35, 128.95],
  경남: [35.45, 128.15],
  제주: [33.48, 126.55],
};

function ringBounds(ring) {
  let minLng = Infinity,
    maxLng = -Infinity,
    minLat = Infinity,
    maxLat = -Infinity;
  for (const [lng, lat] of ring) {
    if (lng < minLng) minLng = lng;
    if (lng > maxLng) maxLng = lng;
    if (lat < minLat) minLat = lat;
    if (lat > maxLat) maxLat = lat;
  }
  return { minLng, maxLng, minLat, maxLat };
}

function ringArea(ring) {
  let area = 0;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const [x1, y1] = ring[i];
    const [x2, y2] = ring[j];
    area += (x2 - x1) * (y2 + y1);
  }
  return Math.abs(area);
}

function pointInRing(point, ring) {
  const [x, y] = point;
  let inside = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const [xi, yi] = ring[i];
    const [xj, yj] = ring[j];
    const intersect =
      yi > y !== yj > y && x < ((xj - xi) * (y - yi)) / (yj - yi + 0.0) + xi;
    if (intersect) inside = !inside;
  }
  return inside;
}

function minDistToEdge(point, ring) {
  const [px, py] = point;
  let min = Infinity;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const [x1, y1] = ring[i];
    const [x2, y2] = ring[j];
    const dx = x2 - x1;
    const dy = y2 - y1;
    const lenSq = dx * dx + dy * dy;
    let t = lenSq === 0 ? 0 : ((px - x1) * dx + (py - y1) * dy) / lenSq;
    t = Math.max(0, Math.min(1, t));
    const cx = x1 + t * dx;
    const cy = y1 + t * dy;
    const dist = Math.hypot(px - cx, py - cy);
    if (dist < min) min = dist;
  }
  return min;
}

function largestRing(feature) {
  const geom = feature.geometry;
  if (!geom) return null;

  const polygons =
    geom.type === 'Polygon'
      ? [geom.coordinates]
      : geom.type === 'MultiPolygon'
        ? geom.coordinates
        : [];

  let bestRing = null;
  let bestArea = 0;
  for (const poly of polygons) {
    const ring = poly[0];
    const area = ringArea(ring);
    if (area > bestArea) {
      bestArea = area;
      bestRing = ring;
    }
  }
  return bestRing;
}

/** 폴리곤 내부에서 가장 여유 있는 지점 [lat, lng] */
export function getInteriorPoint(feature) {
  const ring = largestRing(feature);
  if (!ring) return null;

  const bounds = ringBounds(ring);
  const steps = 14;
  let bestPt = null;
  let bestScore = -1;

  for (let i = 0; i <= steps; i++) {
    for (let j = 0; j <= steps; j++) {
      const lng = bounds.minLng + ((bounds.maxLng - bounds.minLng) * i) / steps;
      const lat = bounds.minLat + ((bounds.maxLat - bounds.minLat) * j) / steps;
      if (!pointInRing([lng, lat], ring)) continue;
      const score = minDistToEdge([lng, lat], ring);
      if (score > bestScore) {
        bestScore = score;
        bestPt = [lat, lng];
      }
    }
  }

  if (bestPt) return bestPt;

  const centerLng = (bounds.minLng + bounds.maxLng) / 2;
  const centerLat = (bounds.minLat + bounds.maxLat) / 2;
  return [centerLat, centerLng];
}

export function getLabelLatLng(feature, shortLabel, currentKey) {
  if (currentKey === 'root' && SIDO_LABEL_POSITIONS[shortLabel]) {
    return SIDO_LABEL_POSITIONS[shortLabel];
  }
  return getInteriorPoint(feature);
}

/** 화면 픽셀 기준 라벨 표시 여부 */
export function shouldShowPermanentLabel(
  featureLayer,
  map,
  currentKey,
  { isActive = false } = {},
) {
  if (currentKey === 'root' || isActive || hasDongDrilldown(currentKey))
    return true;

  const bounds = featureLayer.getBounds();
  const nw = map.latLngToContainerPoint(bounds.getNorthWest());
  const se = map.latLngToContainerPoint(bounds.getSouthEast());
  const minSide = Math.min(Math.abs(se.x - nw.x), Math.abs(se.y - nw.y));

  return minSide >= 18;
}
