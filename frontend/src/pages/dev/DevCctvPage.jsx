import { useState } from "react"
import { analyzeVideo, API_V1 } from "../../api/client"
import ApiResult, { parseApiError } from "./components/ApiResult"
import DevPageHead from "./components/DevPageHead"
import "./DevCommon.css"

const SAMPLE_SMS =
  "실종자 안내\n이름: 김철수\n나이: 75세\n성별: 남\n착의: 검은 패딩"

/** Dev — POST /api/v1/cctv/analyze (영상+안내문자 업로드 → 탐지 파이프라인) */
export default function DevCctvPage() {
  const [smsText, setSmsText] = useState(SAMPLE_SMS)
  const [videoFile, setVideoFile] = useState(null)
  const [refFile, setRefFile] = useState(null)
  const [region, setRegion] = useState("")
  const [status, setStatus] = useState("idle")
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)

  /** multipart/form-data로 영상·문자·참조사진·지역 전송 */
  const analyze = async () => {
    if (!videoFile) return
    setStatus("loading")
    setError(null)
    try {
      const formData = new FormData()
      formData.append("sms_text", smsText)
      formData.append("video", videoFile)
      if (refFile) formData.append("reference_photo", refFile)
      if (region.trim()) formData.append("region", region.trim())
      const result = await analyzeVideo(formData)
      setData(result)
      setStatus("ok")
    } catch (err) {
      setError(parseApiError(err))
      setStatus("err")
    }
  }

  return (
    <>
      <DevPageHead
        title="CCTV 분석"
        desc="영상 업로드 후 파이프라인을 실행합니다. 처리 시간이 길 수 있습니다."
      />

      <div className="dev-section">
        <h2>POST {API_V1}/cctv/analyze</h2>
        <div className="dev-form">
          <label htmlFor="dev-cctv-sms">안내문자</label>
          <textarea
            id="dev-cctv-sms"
            value={smsText}
            onChange={(e) => setSmsText(e.target.value)}
            rows={5}
          />
          <label htmlFor="dev-cctv-video">영상 파일</label>
          <input
            id="dev-cctv-video"
            type="file"
            accept="video/*"
            onChange={(e) => setVideoFile(e.target.files?.[0] ?? null)}
          />
          <label htmlFor="dev-cctv-ref">참조 사진 (선택)</label>
          <input
            id="dev-cctv-ref"
            type="file"
            accept="image/*"
            onChange={(e) => setRefFile(e.target.files?.[0] ?? null)}
          />
          <label htmlFor="dev-cctv-region">지역 (선택)</label>
          <input
            id="dev-cctv-region"
            value={region}
            onChange={(e) => setRegion(e.target.value)}
            placeholder="서울특별시"
          />
          <button
            type="button"
            className="dev-btn"
            disabled={!smsText.trim() || !videoFile}
            onClick={analyze}
          >
            분석 실행
          </button>
        </div>
        <ApiResult status={status} data={data} error={error} />
      </div>
    </>
  )
}
