# GeoJSON 행정구역 데이터

- 시/도: `korea.topo.json` — [southkorea-maps](https://github.com/southkorea/southkorea-maps) TopoJSON (17개, 고해상도)
- 시/군/구: `municipalities.topo.json` — 동일 출처 TopoJSON (251개)
- 읍/면/동: **admdongkor** 런타임 로딩 (구 클릭 시 `sggcd` 필터, 20250401 경계)
- (레거시) `sigungu/1122.geojson` — 강남구 프로토타입 정적 파일, 더 이상 사용하지 않음

런타임에서 `topojson-client`로 GeoJSON 변환 후 렌더링합니다.

실제 서비스에서는 최신 공공데이터(통계청/VWorld/admdongkor)로 교체할 수 있습니다.
