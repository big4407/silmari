import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { analyzeVideo } from "../api/client"
import { useDetectionStore } from "../store/useDetectionStore"
import "./FormPage.css"

export default function CCTVUpload() {
  const navigate = useNavigate()
  const {
    alertText, setAlertText, selectedRegion, setActiveSearch,
  } = useDetectionStore()
  const [videoFile, setVideoFile] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const handleSubmit = async () => {
    if (!alertText.trim() || !videoFile) {
      setError("안내문자와 CCTV 영상을 모두 입력해주세요.")
      return
    }
    setError(null)
    setLoading(true)

    try {
      const formData = new FormData()
      formData.append("sms_text", alertText)
      formData.append("video", videoFile)
      if (selectedRegion && selectedRegion !== "전국") {
        formData.append("region", selectedRegion)
      }

      const result = await analyzeVideo(formData)
      const sms = result.sms_info || {}

      setActiveSearch({
        alertText: alertText.trim(),
        smsInfo: sms,
        region: selectedRegion !== "전국" ? selectedRegion : null,
      })

      navigate("/search-results")
    } catch {
      setError("분석 중 오류가 발생했습니다.")
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="form-page">
      <h1>CCTV 분석</h1>
      <p className="form-page__desc">
        실종 안내문자와 CCTV 영상을 입력하면 AI가 인상착의를 파싱하고 실종자 후보를 탐지합니다.
      </p>

      <label className="form-page__label">안전안내문자</label>
      <textarea
        className="form-page__textarea"
        placeholder="예) 실종자 홍길동(남, 65세)은 검은 점퍼와 파란 바지를 착용하고 있습니다."
        value={alertText}
        onChange={e => setAlertText(e.target.value)}
        rows={5}
      />

      <label className="form-page__label">CCTV 영상</label>
      <input type="file" accept="video/*" onChange={e => setVideoFile(e.target.files[0])} />

      {error && <p className="form-page__error">{error}</p>}

      <button className="form-page__btn" onClick={handleSubmit} disabled={loading}>
        {loading ? "분석 중..." : "탐지 시작"}
      </button>
    </div>
  )
}
