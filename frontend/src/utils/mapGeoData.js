/**
 * Leaflet용 행정구역 GeoJSON 로드·스타일·라벨 유틸.
 * public/geodata/ + southkorea-maps TopoJSON 변환.
 */
import * as topojson from 'topojson-client';
import { hasDongDrilldown } from '../data/dongRegions';
import { REGION_DATA } from '../data/regionData';
import { loadDongGeoJson } from './admDongLoader';
import { SIDO_SEARCH_TERMS } from './regionMatch';

/** REGION_DATA 행정코드 → southkorea-maps GeoJSON 시도코드 */
export const GEO_SIDO_CODE_MAP = {
  11: '11',
  26: '21',
  27: '22',
  28: '23',
  29: '24',
  30: '25',
  36: '29',
  31: '26',
  41: '31',
  42: '32',
  43: '33',
  44: '34',
  45: '35',
  46: '36',
  47: '37',
  48: '38',
  50: '39',
};

const REGION_COLORS = [
  '#9eb8d4',
  '#c5daf0',
  '#7da4c4',
  '#d8eaf8',
  '#8aaccc',
  '#b4cfe8',
  '#e4f0fa',
  '#6d96b8',
  '#cddff2',
  '#a0bcd8',
  '#d0e6f6',
  '#88a8c8',
  '#bdd4ee',
  '#eef6fc',
  '#7898b4',
  '#b0cce4',
  '#dcecf8',
];

let municipalitiesCache = null;

async function loadTopoCollection(topoFile, objectName) {
  const res = await fetch(topoFile);
  const topology = await res.json();
  return topojson.feature(topology, topology.objects[objectName]);
}

async function loadMunicipalities() {
  if (!municipalitiesCache) {
    municipalitiesCache = await loadTopoCollection(
      '/geodata/municipalities.topo.json',
      'skorea_municipalities_geo',
    );
  }
  return municipalitiesCache;
}

export async function loadMapGeoJson(currentKey, options = {}) {
  if (currentKey === 'root') {
    return loadTopoCollection(
      '/geodata/korea.topo.json',
      'skorea_provinces_geo',
    );
  }

  if (hasDongDrilldown(currentKey)) {
    return loadDongGeoJson(currentKey, options);
  }

  const geoSido = GEO_SIDO_CODE_MAP[currentKey];
  if (!geoSido) {
    return { type: 'FeatureCollection', features: [] };
  }

  const data = await loadMunicipalities();
  return {
    type: 'FeatureCollection',
    features: data.features.filter((f) =>
      String(f.properties?.code || '').startsWith(geoSido),
    ),
  };
}

export function getRegionColor(index) {
  return REGION_COLORS[index % REGION_COLORS.length];
}

export function getRegionStyle({ isActive, alertCount = 0 }) {
  if (isActive) {
    return {
      fillColor: '#0066cc',
      fillOpacity: 0.9,
      color: '#003876',
      weight: 2.5,
    };
  }

  const count = alertCount || 0;
  if (count >= 5) {
    return {
      fillColor: '#2d6ba8',
      fillOpacity: 0.9,
      color: '#003876',
      weight: 2,
    };
  }
  if (count >= 3) {
    return {
      fillColor: '#4d8cc8',
      fillOpacity: 0.88,
      color: '#003876',
      weight: 2,
    };
  }
  if (count >= 1) {
    return {
      fillColor: '#7eb3e0',
      fillOpacity: 0.86,
      color: '#004ea2',
      weight: 1.8,
    };
  }

  return {
    fillColor: '#c5d8ea',
    fillOpacity: 0.78,
    color: '#6a8094',
    weight: 1.2,
  };
}

function matchSidoRegion(geoName) {
  for (const region of REGION_DATA.root.regions) {
    const terms = SIDO_SEARCH_TERMS[region.label] || [region.label];
    if (terms.some((term) => geoName.includes(term))) {
      return region;
    }
  }
  return null;
}

function matchGuRegion(geoName, sidoKey) {
  const regions = REGION_DATA[sidoKey]?.regions;
  if (!regions) return null;
  return (
    regions.find((r) => geoName.includes(r.label) || r.label === geoName) ||
    null
  );
}

export function findRegionForFeature(feature, currentKey) {
  const geoName =
    feature.properties?.name ||
    feature.properties?.emdnm ||
    feature.properties?.SIG_KOR_NM ||
    '';

  if (currentKey === 'root') {
    return matchSidoRegion(geoName);
  }

  if (hasDongDrilldown(currentKey)) {
    const code =
      feature.properties?.code ||
      feature.properties?.emdcd ||
      feature.properties?.emd8;
    return {
      id: String(code || geoName),
      label: geoName,
      lat: null,
      lng: null,
    };
  }

  const matched = matchGuRegion(geoName, currentKey);
  if (matched) return matched;

  return {
    id: String(feature.properties?.code || geoName),
    label: geoName,
    lat: null,
    lng: null,
  };
}

export function getShortLabel(name, currentKey) {
  if (currentKey === 'root') {
    for (const region of REGION_DATA.root.regions) {
      const terms = SIDO_SEARCH_TERMS[region.label] || [region.label];
      if (terms.some((term) => name.includes(term))) {
        return region.label;
      }
    }
    return name.replace(/특별자치시|특별자치도|광역시|특별시|도$/g, '');
  }
  if (hasDongDrilldown(currentKey)) {
    return name.replace(/\(.*\)/, '').trim();
  }
  const cleaned = name.replace(/\(.*\)/, '').trim();
  const compound = cleaned.match(/^(.+시)(.+[구군])$/);
  if (compound) return compound[2];
  return cleaned;
}

/** 선택된 지역과 GeoJSON feature 매칭 (성남시 ↔ 성남시분당구 등) */
export function isRegionSelected(
  selectedRegion,
  regionLabel,
  geoName,
  shortLabel,
  currentKey = 'root',
) {
  if (!selectedRegion || selectedRegion === '전국') return false;

  if (currentKey === 'root') {
    if (selectedRegion === regionLabel || selectedRegion === shortLabel)
      return true;
    const geo = geoName || regionLabel || '';
    const selectedTerms = SIDO_SEARCH_TERMS[selectedRegion] || [selectedRegion];
    const featureTerms = SIDO_SEARCH_TERMS[regionLabel] || [regionLabel];
    return (
      selectedTerms.some((term) => geo.includes(term)) &&
      featureTerms.some((term) => geo.includes(term))
    );
  }

  if (selectedRegion === regionLabel || selectedRegion === shortLabel)
    return true;

  const sel = selectedRegion.replace(/\s/g, '');
  const geo = (geoName || regionLabel || '').replace(/\s/g, '');
  if (!geo || !sel) return false;

  if (hasDongDrilldown(currentKey)) {
    return geo.includes(sel) || sel.includes(geo);
  }

  if (geo.includes(sel)) return true;

  const cityGu = sel.match(/^(.+시)(.+[구군])$/);
  if (cityGu && geo.includes(cityGu[1]) && geo.includes(cityGu[2])) return true;

  const cityOnly = sel.match(/^(.+시)$/);
  if (cityOnly && geo.startsWith(cityOnly[1])) return true;

  return false;
}
