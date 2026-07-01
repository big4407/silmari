/** 탐지 구간별 MP4 클립 순차 재생 — /api/result/media/clips URL 사용 */
import { useEffect, useRef, useState } from "react"
import "./ClipSequencePlayer.css"

export default function ClipSequencePlayer({ clips, onBack }) {
  const videoRef = useRef(null)
  const [currentIndex, setCurrentIndex] = useState(0)
  const [playError, setPlayError] = useState(null)

  useEffect(() => {
    setCurrentIndex(0)
    setPlayError(null)
  }, [clips])

  useEffect(() => {
    const video = videoRef.current
    if (!video || !clips?.length) return
    setPlayError(null)
    video.load()
    video.play().catch(() => {
      setPlayError("자동 재생이 차단되었습니다. 재생 버튼을 눌러주세요.")
    })
  }, [currentIndex, clips])

  const handleEnded = () => {
    if (currentIndex < clips.length - 1) {
      setCurrentIndex(prev => prev + 1)
    }
  }

  const handleVideoError = () => {
    setPlayError("영상을 불러올 수 없습니다. CCTV 영상을 다시 분석해주세요.")
  }

  if (!clips?.length) {
    return <div className="clip-player clip-player--empty">재생할 클립이 없습니다.</div>
  }

  const current = clips[currentIndex]

  return (
    <div className="clip-player">
      <button type="button" className="clip-player__back" onClick={onBack}>
        ← 목록
      </button>

      <video
        ref={videoRef}
        key={current.url}
        src={current.url}
        controls
        playsInline
        preload="auto"
        className="clip-player__video"
        onEnded={handleEnded}
        onError={handleVideoError}
      />

      {playError && <p className="clip-player__error">{playError}</p>}

      <div className="clip-player__meta">
        <span>구간 {currentIndex + 1} / {clips.length}</span>
        <span>{current.start_sec}초 ~ {current.end_sec}초</span>
      </div>
    </div>
  )
}
