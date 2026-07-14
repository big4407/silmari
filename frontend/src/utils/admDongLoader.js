/**
 * admdongkor 기반 읍·면·동 경계 로더.
 * 구 클릭 시 해당 시군구(sggcd) 행정동만 필터해 GeoJSON 반환.
 */
import * as adk from 'admdongkor';
import { REGION_DATA, findGuInSido, findSidoIdForGu } from '../data/regionData';

const ADM_VERSION = '20250401';
const ADM_PARQUET_BASE_URLS = [
  'https://cdn.jsdelivr.net/gh/vuski/admdongkor@master/parquet',
  'https://raw.githubusercontent.com/vuski/admdongkor/master/parquet',
];

/** REGION_DATA 시도 id → admdongkor sidocd */
export const ADM_SIDO_CODE_MAP = {
  11: '11',
  26: '26',
  27: '27',
  28: '28',
  29: '29',
  30: '30',
  36: '36',
  31: '31',
  41: '41',
  42: '51',
  43: '43',
  44: '44',
  45: '52',
  46: '46',
  47: '47',
  48: '48',
  50: '50',
};

/** admdongkor sidocd → REGION_DATA 시도 id */
export const REGION_SIDO_FROM_ADM = Object.fromEntries(
  Object.entries(ADM_SIDO_CODE_MAP).map(([regionId, admCd]) => [
    admCd,
    regionId,
  ]),
);

let emdFeaturesCache = null;
let sggFeaturesCache = null;
const dongGeoCache = new Map();

function normalizeLabel(label) {
  return (label || '').replace(/\s/g, '');
}

export { findGuInSido, findSidoIdForGu };

export function isGuKey(key) {
  return findSidoIdForGu(key) != null;
}

async function loadAdmFeatures(level) {
  let lastError = null;
  for (const baseUrl of ADM_PARQUET_BASE_URLS) {
    try {
      const data = await adk.get(ADM_VERSION, level, { detail: false, baseUrl });
      return data.features;
    } catch (error) {
      lastError = error;
    }
  }
  throw lastError || new Error(`failed to load admdongkor ${level}`);
}

async function loadSggFeatures() {
  if (!sggFeaturesCache) {
    sggFeaturesCache = await loadAdmFeatures('sgg');
  }
  return sggFeaturesCache;
}

async function loadEmdFeatures() {
  if (!emdFeaturesCache) {
    emdFeaturesCache = await loadAdmFeatures('emd');
  }
  return emdFeaturesCache;
}

export async function resolveSggcd(sidoId, guLabel) {
  const sidocd = ADM_SIDO_CODE_MAP[sidoId];
  if (!sidocd || !guLabel) return null;

  const sggList = await loadSggFeatures();
  const target = normalizeLabel(guLabel);
  const inSido = sggList.filter((f) => f.properties.sidocd === sidocd);
  const match =
    inSido.find((f) => normalizeLabel(f.properties.sggnm) === target) ||
    inSido.find((f) => {
      const name = normalizeLabel(f.properties.sggnm);
      return name.includes(target) || target.includes(name);
    });
  return match?.properties?.sggcd || null;
}

function normalizeEmdGeoJson(features) {
  return {
    type: 'FeatureCollection',
    features: features.map((f) => ({
      ...f,
      properties: {
        ...f.properties,
        name: f.properties.emdnm,
        code: String(f.properties.emdcd || f.properties.emd8 || ''),
        emdnm: f.properties.emdnm,
      },
    })),
  };
}

function resolveGuContext(guKey, { sidoId, guLabel } = {}) {
  if (sidoId && guLabel) {
    return { sidoId, guLabel };
  }

  const ctx = findSidoIdForGu(guKey);
  if (ctx) {
    return { sidoId: ctx.sidoId, guLabel: ctx.gu.label };
  }

  if (sidoId && guLabel) {
    return { sidoId, guLabel };
  }

  return null;
}

export async function loadDongGeoJson(guKey, options = {}) {
  const ctx = resolveGuContext(guKey, options);
  if (!ctx) {
    return { type: 'FeatureCollection', features: [] };
  }

  const cacheKey = `${ctx.sidoId}:${normalizeLabel(ctx.guLabel)}`;
  if (dongGeoCache.has(cacheKey)) {
    return dongGeoCache.get(cacheKey);
  }

  const sggcd = await resolveSggcd(ctx.sidoId, ctx.guLabel);
  if (!sggcd) {
    return { type: 'FeatureCollection', features: [] };
  }

  const allEmd = await loadEmdFeatures();
  const sggcdKey = String(sggcd);
  const features = allEmd.filter(
    (f) => String(f.properties.sggcd) === sggcdKey,
  );
  const geojson = normalizeEmdGeoJson(features);
  dongGeoCache.set(cacheKey, geojson);
  return geojson;
}

export function getGuLabelFromPath(path) {
  if (!path || path.length < 3) return null;
  const sidoId = path[1];
  const guKey = path[2];
  const gu = REGION_DATA[sidoId]?.regions?.find((r) => r.id === guKey);
  if (gu?.label) return gu.label;

  const ctx = findSidoIdForGu(guKey);
  return ctx?.gu?.label || null;
}
