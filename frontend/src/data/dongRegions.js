/** 동 단위 드릴다운 프로토타입 — 서울 강남구 (admdongkor 20250401 경계) */

export const DONG_DRILLDOWN_GU = new Set(["1122"])

export const GANGNAM_DONG_REGIONS = [
  { id: "1168051000", label: "신사동", lat: 37.5258, lng: 127.0202 },
  { id: "1168052100", label: "논현1동", lat: 37.5121, lng: 127.0267 },
  { id: "1168053100", label: "논현2동", lat: 37.5151, lng: 127.0359 },
  { id: "1168054500", label: "압구정동", lat: 37.5277, lng: 127.0341 },
  { id: "1168056500", label: "청담동", lat: 37.5257, lng: 127.0522 },
  { id: "1168058000", label: "삼성1동", lat: 37.5162, lng: 127.0594 },
  { id: "1168059000", label: "삼성2동", lat: 37.5114, lng: 127.0490 },
  { id: "1168060000", label: "대치1동", lat: 37.4933, lng: 127.0590 },
  { id: "1168061000", label: "대치2동", lat: 37.5002, lng: 127.0661 },
  { id: "1168063000", label: "대치4동", lat: 37.5020, lng: 127.0550 },
  { id: "1168064000", label: "역삼1동", lat: 37.4999, lng: 127.0361 },
  { id: "1168065000", label: "역삼2동", lat: 37.4984, lng: 127.0449 },
  { id: "1168065500", label: "도곡1동", lat: 37.4896, lng: 127.0407 },
  { id: "1168065600", label: "도곡2동", lat: 37.4880, lng: 127.0490 },
  { id: "1168066000", label: "개포1동", lat: 37.4803, lng: 127.0644 },
  { id: "1168067000", label: "개포2동", lat: 37.4860, lng: 127.0670 },
  { id: "1168067500", label: "개포3동", lat: 37.4942, lng: 127.0812 },
  { id: "1168069000", label: "개포4동", lat: 37.4767, lng: 127.0532 },
  { id: "1168070000", label: "세곡동", lat: 37.4718, lng: 127.1034 },
  { id: "1168072000", label: "일원본동", lat: 37.4832, lng: 127.0839 },
  { id: "1168073000", label: "일원1동", lat: 37.4931, lng: 127.0908 },
  { id: "1168075000", label: "수서동", lat: 37.4854, lng: 127.1015 },
]

export const DONG_REGION_DATA = {
  1122: {
    label: "강남구",
    center: [37.5172, 127.0473],
    zoom: 13,
    regions: GANGNAM_DONG_REGIONS,
  },
}

export function hasDongDrilldown(guId) {
  return DONG_DRILLDOWN_GU.has(guId)
}
