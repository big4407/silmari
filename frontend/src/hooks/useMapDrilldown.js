/**
 * 지도 드릴다운 상태 훅 — 전국 → 시·도 → 구·군 → 동 네비게이션.
 * MapDrilldown 과 regionMatch.buildMapFilter 연동.
 */
import { useState, useCallback, useMemo, useRef } from 'react';
import { REGION_DATA } from '../data/regionData';
import { hasDongDrilldown } from '../data/dongRegions';
import { buildMapFilter } from '../utils/regionMatch';

export { REGION_DATA };

const SIDO_ONLY_ZOOM = 9;
const GU_ZOOM = 13;
const DONG_ZOOM = 14;

export default function useMapDrilldown(onRegionSelect) {
  const [path, setPath] = useState(['root']);
  const [selectedRegion, setSelectedRegion] = useState('전국');
  const [sidoFocus, setSidoFocus] = useState(null);
  const [guFocus, setGuFocus] = useState(null);
  const [dongFocus, setDongFocus] = useState(null);
  const [activeGu, setActiveGu] = useState(null);

  const onRegionSelectRef = useRef(onRegionSelect);
  onRegionSelectRef.current = onRegionSelect;

  const currentKey = path[path.length - 1];
  const drillData = REGION_DATA[currentKey] || REGION_DATA.root;

  const mapView = useMemo(() => {
    if (dongFocus?.lat != null && dongFocus?.lng != null) {
      return { center: [dongFocus.lat, dongFocus.lng], zoom: DONG_ZOOM };
    }
    if (guFocus) {
      return { center: [guFocus.lat, guFocus.lng], zoom: GU_ZOOM };
    }
    if (sidoFocus) {
      return { center: [sidoFocus.lat, sidoFocus.lng], zoom: SIDO_ONLY_ZOOM };
    }
    return { center: drillData.center, zoom: drillData.zoom };
  }, [dongFocus, guFocus, sidoFocus, drillData]);

  const displayRegions = drillData.regions;

  const breadcrumbs = useMemo(() => {
    const crumbs = path.map((key) => ({
      key,
      label:
        key === 'root'
          ? '전국'
          : REGION_DATA[key]?.label ||
            REGION_DATA.root.regions.find((r) => r.id === key)?.label ||
            key,
    }));
    if (dongFocus && hasDongDrilldown(path[path.length - 1])) {
      crumbs.push({ key: `dong-${dongFocus.id}`, label: dongFocus.label });
    } else if (guFocus && path.length > 1 && path.length <= 2) {
      crumbs.push({ key: `gu-${guFocus.id}`, label: guFocus.label });
    } else if (sidoFocus && path.length === 1) {
      crumbs.push({ key: `sido-${sidoFocus.id}`, label: sidoFocus.label });
    }
    return crumbs;
  }, [path, sidoFocus, guFocus, dongFocus]);

  const applyFocus = useCallback((focus) => {
    if (!focus?.path) return;
    // 안내문자 클릭 등 "카메라만 이동"하는 포커스는 applyFilter:false로 표시된다.
    // 이 경우 지도 카메라(줌/센터)는 옮기지만 사이드바 목록 필터(mapFilter)는
    // 건드리지 않아, 클릭한 문자에 따라 다른 카드가 화면에서 사라지는 문제를 막는다.
    const notifyFilter = focus.applyFilter !== false;
    setSidoFocus(null);
    setGuFocus(null);
    setDongFocus(null);
    setActiveGu(null);
    setPath(focus.path);
    setSelectedRegion(focus.selectedLabel || '전국');

    if (focus.path.length > 2) {
      const sidoId = focus.path[1];
      const guId = focus.path[2];
      const gu = REGION_DATA[sidoId]?.regions?.find((r) => r.id === guId);
      if (gu) {
        setActiveGu({ id: gu.id, label: gu.label });
      } else if (focus.guLabel || focus.mapFilter?.guLabel) {
        setActiveGu({
          id: guId,
          label: focus.guLabel || focus.mapFilter.guLabel,
        });
      }
    }

    if (focus.mapFilter) {
      if (notifyFilter) onRegionSelectRef.current?.(focus.mapFilter);
      if (focus.path.length > 2 && focus.mapFilter?.level === 'dong') {
        setDongFocus({
          id: focus.dongId || focus.selectedLabel,
          label: focus.selectedLabel,
          lat: focus.lat ?? null,
          lng: focus.lng ?? null,
        });
        return;
      }
      if (focus.path.length > 1) {
        const sidoId = focus.path[1];
        const gu = REGION_DATA[sidoId]?.regions?.find(
          (r) => r.label === focus.selectedLabel,
        );
        if (gu) {
          setGuFocus(gu);
        } else if (focus.mapFilter.level === 'gu') {
          setGuFocus({
            id: `geo-${focus.selectedLabel}`,
            label: focus.selectedLabel,
            lat: null,
            lng: null,
          });
        }
      }
      return;
    }

    const lastKey = focus.path[focus.path.length - 1];
    if (lastKey === 'root') {
      if (notifyFilter) onRegionSelectRef.current?.({ level: 'nation' });
      return;
    }

    const sidoId = focus.path[1];
    const gu = REGION_DATA[sidoId]?.regions?.find(
      (r) => r.label === focus.selectedLabel,
    );
    if (gu) {
      setGuFocus(gu);
      if (notifyFilter) onRegionSelectRef.current?.(buildMapFilter(gu, focus.path));
      return;
    }

    const sido = REGION_DATA.root.regions.find((r) => r.id === sidoId);
    if (sido && notifyFilter) {
      onRegionSelectRef.current?.(buildMapFilter(sido, focus.path));
    }
  }, []);

  const selectRegion = useCallback(
    (region) => {
      const isSido = REGION_DATA.root.regions.some((r) => r.id === region.id);
      const inSidoView = path.length === 2;
      const inDongView = path.length === 3 && hasDongDrilldown(path[2]);

      if (path.length === 1 && isSido) {
        setSidoFocus(null);
        setGuFocus(null);
        setDongFocus(null);
        const nextPath = [...path, region.id];
        setPath(nextPath);
        setSelectedRegion(region.label);
        onRegionSelectRef.current?.(buildMapFilter(region, nextPath));
        return;
      }

      if (inDongView) {
        setSidoFocus(null);
        setGuFocus(null);
        setDongFocus(region);
        setSelectedRegion(region.label);
        onRegionSelectRef.current?.(buildMapFilter(region, path));
        return;
      }

      if (inSidoView) {
        setSidoFocus(null);
        if (hasDongDrilldown(region.id)) {
          setGuFocus(null);
          setDongFocus(null);
          setActiveGu({ id: region.id, label: region.label });
          const nextPath = [...path, region.id];
          setPath(nextPath);
          setSelectedRegion(region.label);
          onRegionSelectRef.current?.(buildMapFilter(region, nextPath));
          return;
        }
        setGuFocus(region);
        setDongFocus(null);
        setSelectedRegion(region.label);
        onRegionSelectRef.current?.(buildMapFilter(region, path));
        return;
      }

      if (isSido) {
        setPath(['root']);
        setSidoFocus(region);
        setGuFocus(null);
        setDongFocus(null);
        setSelectedRegion(region.label);
        onRegionSelectRef.current?.(
          buildMapFilter(region, ['root', region.id]),
        );
      }
    },
    [path],
  );

  const navigateTo = useCallback(
    (index) => {
      const crumb = breadcrumbs[index];
      if (!crumb) return;

      if (crumb.key === 'root') {
        setPath(['root']);
        setSidoFocus(null);
        setGuFocus(null);
        setDongFocus(null);
        setActiveGu(null);
        setSelectedRegion('전국');
        onRegionSelectRef.current?.({ level: 'nation' });
        return;
      }

      if (crumb.key.startsWith('sido-')) {
        const sido = REGION_DATA.root.regions.find(
          (r) => r.id === crumb.key.replace('sido-', ''),
        );
        if (!sido) return;
        setPath(['root']);
        setSidoFocus(sido);
        setGuFocus(null);
        setDongFocus(null);
        setSelectedRegion(sido.label);
        onRegionSelectRef.current?.(buildMapFilter(sido, ['root', sido.id]));
        return;
      }

      if (crumb.key.startsWith('gu-')) {
        const gu = REGION_DATA[path[1]]?.regions?.find(
          (r) => r.id === crumb.key.replace('gu-', ''),
        );
        if (!gu) return;
        setGuFocus(gu);
        setDongFocus(null);
        setSelectedRegion(gu.label);
        onRegionSelectRef.current?.(buildMapFilter(gu, path));
        return;
      }

      if (crumb.key.startsWith('dong-')) {
        const dongId = crumb.key.replace('dong-', '');
        const dong = { id: dongId, label: crumb.label, lat: null, lng: null };
        setDongFocus(dong);
        setSelectedRegion(dong.label);
        onRegionSelectRef.current?.(buildMapFilter(dong, path));
        return;
      }

      const keyIndex = path.indexOf(crumb.key);
      if (keyIndex < 0) return;
      const newPath = path.slice(0, keyIndex + 1);
      setPath(newPath);
      setSidoFocus(null);
      setGuFocus(null);
      setDongFocus(null);
      if (newPath.length < 3) {
        setActiveGu(null);
      } else if (hasDongDrilldown(crumb.key)) {
        const gu = REGION_DATA[newPath[1]]?.regions?.find(
          (r) => r.id === crumb.key,
        );
        if (gu) {
          setActiveGu({ id: gu.id, label: gu.label });
        }
      }
      const label = REGION_DATA[crumb.key]?.label || crumb.label;
      setSelectedRegion(label);
      const sido = REGION_DATA.root.regions.find((r) => r.id === crumb.key);
      if (hasDongDrilldown(crumb.key)) {
        const gu = REGION_DATA[newPath[1]]?.regions?.find(
          (r) => r.id === crumb.key,
        );
        onRegionSelectRef.current?.(
          gu ? buildMapFilter(gu, newPath) : { level: 'nation' },
        );
        return;
      }
      onRegionSelectRef.current?.(
        sido ? buildMapFilter(sido, newPath) : { level: 'nation' },
      );
    },
    [path, breadcrumbs],
  );

  const resetMap = useCallback(() => {
    setPath(['root']);
    setSidoFocus(null);
    setGuFocus(null);
    setDongFocus(null);
    setActiveGu(null);
    setSelectedRegion('전국');
    onRegionSelectRef.current?.({ level: 'nation' });
  }, []);

  return {
    path,
    currentKey,
    activeGu,
    mapView,
    displayRegions,
    breadcrumbs,
    selectedRegion,
    selectRegion,
    navigateTo,
    resetMap,
    applyFocus,
  };
}
