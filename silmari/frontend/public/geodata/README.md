# GeoJSON 행정구역 데이터

- 시/도: `korea.topo.json` — [southkorea-maps](https://github.com/southkorea/southkorea-maps) TopoJSON (17개, 고해상도)
- 시/군/구: `municipalities.topo.json` — 동일 출처 TopoJSON (251개)

런타임에서 `topojson-client`로 GeoJSON 변환 후 렌더링합니다.

실제 서비스에서는 최신 공공데이터(통계청/VWorld/admdongkor)로 교체할 수 있습니다.

- 읍/면/동: `sigungu/{행정코드}.geojson` (미구현)
