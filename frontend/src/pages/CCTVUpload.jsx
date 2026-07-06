/**
 * CCTV 업로드·분석 요청 페이지.
 */
import { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { analyzeVideo } from '../api/client';
import { useDetectionStore } from '../store/useDetectionStore';
import { formatFileSize, previewAlertText } from '../utils/alertPreview';
import './FormPage.css';

const ANALYSIS_STEPS = [
  '안내문자 파싱 중…',
  '영상 프레임 분석 중…',
  '후보 탐지 중…',
  '결과 저장 중…',
];

export default function CCTVUpload() {
  const navigate = useNavigate();
  const { alertText, setAlertText, selectedRegion, setActiveSearch } =
    useDetectionStore();
  const [videoFile, setVideoFile] = useState(null);
  const [photoFile, setPhotoFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [stepIndex, setStepIndex] = useState(0);

  const preview = useMemo(() => previewAlertText(alertText), [alertText]);

  const currentStep = useMemo(() => {
    if (alertText.trim() && videoFile) return 3;
    if (videoFile) return 2;
    if (alertText.trim()) return 1;
    return 0;
  }, [alertText, videoFile]);

  useEffect(() => {
    if (!loading) {
      setStepIndex(0);
      return undefined;
    }

    const timer = setInterval(() => {
      setStepIndex((prev) => (prev + 1) % ANALYSIS_STEPS.length);
    }, 1400);

    return () => clearInterval(timer);
  }, [loading]);

  const handleSubmit = async () => {
    if (!alertText.trim() || !videoFile) {
      setError('안내문자와 CCTV 영상을 모두 입력해주세요.');
      return;
    }
    setError(null);
    setLoading(true);

    try {
      const formData = new FormData();
      formData.append('sms_text', alertText);
      formData.append('video', videoFile);
      if (photoFile) formData.append('reference_photo', photoFile);
      if (selectedRegion && selectedRegion !== '전국') {
        formData.append('region', selectedRegion);
      }

      const result = await analyzeVideo(formData);
      const sms = result.sms_info || {};

      setActiveSearch({
        alertText: alertText.trim(),
        smsInfo: sms,
        region: selectedRegion !== '전국' ? selectedRegion : null,
        searchResultId: result.search_result_id ?? null,
        analysisSummary: {
          totalDetections: result.total_detections ?? 0,
          videoFilename: videoFile.name,
          noMatch: !result.search_result_id,
          demoMode: Boolean(result.demo_mode),
        },
      });

      navigate('/search-results');
    } catch {
      setError('분석 중 오류가 발생했습니다.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="form-page">
      <Link to="/dashboard" className="form-page__back">
        ← 실종자 검색으로 돌아가기
      </Link>

      <h1>CCTV 분석</h1>
      <p className="form-page__desc">
        실종 안내문자와 CCTV 영상을 입력하면 AI가 인상착의를 파싱하고 실종자
        후보를 탐지합니다.
      </p>

      <ol className="form-page__steps" aria-label="분석 단계">
        <li className={currentStep >= 1 ? 'form-page__step--done' : ''}>
          <span>1</span> 안내문자
        </li>
        <li className={currentStep >= 2 ? 'form-page__step--done' : ''}>
          <span>2</span> 영상 업로드
        </li>
        <li className={currentStep >= 3 ? 'form-page__step--done' : ''}>
          <span>3</span> 탐지 실행
        </li>
      </ol>

      <div className="form-page__context">
        {selectedRegion && selectedRegion !== '전국' && (
          <span className="form-page__chip">지역 · {selectedRegion}</span>
        )}
        {preview.name && (
          <span className="form-page__chip form-page__chip--primary">
            {preview.name}
            {preview.age ? ` (${preview.age}세)` : ''}
            {preview.gender ? ` · ${preview.gender}` : ''}
          </span>
        )}
        {preview.clothes && (
          <span className="form-page__chip">인상착의 · {preview.clothes}</span>
        )}
      </div>

      <label className="form-page__label" htmlFor="cctv-alert">
        안전안내문자
      </label>
      <textarea
        id="cctv-alert"
        className="form-page__textarea"
        placeholder="예) 실종자 홍길동(남, 65세)은 검은 점퍼와 파란 바지를 착용하고 있습니다."
        value={alertText}
        onChange={(e) => setAlertText(e.target.value)}
        rows={5}
      />
      <p className="form-page__hint">{alertText.trim().length}자 입력됨</p>

      <label className="form-page__label" htmlFor="cctv-video">
        CCTV 영상
      </label>
      <input
        id="cctv-video"
        type="file"
        accept="video/*"
        onChange={(e) => setVideoFile(e.target.files?.[0] || null)}
      />
      {videoFile && (
        <div className="form-page__file-chip">
          <span>{videoFile.name}</span>
          <span className="form-page__file-size">
            {formatFileSize(videoFile.size)}
          </span>
        </div>
      )}

      <label className="form-page__label" htmlFor="cctv-photo">
        실종자 사진 (선택)
      </label>
      <input
        id="cctv-photo"
        type="file"
        accept="image/*"
        onChange={(e) => setPhotoFile(e.target.files?.[0] || null)}
      />
      {photoFile && (
        <div className="form-page__file-chip">
          <span>{photoFile.name}</span>
          <span className="form-page__file-size">
            {formatFileSize(photoFile.size)}
          </span>
        </div>
      )}

      {error && <p className="form-page__error">{error}</p>}

      <button
        type="button"
        className="form-page__btn"
        onClick={handleSubmit}
        disabled={loading || !alertText.trim() || !videoFile}
      >
        {loading ? '분석 중...' : '탐지 시작'}
      </button>

      {loading && (
        <div className="form-page__loading" role="status" aria-live="polite">
          <div className="form-page__loading-bar" />
          <p>{ANALYSIS_STEPS[stepIndex]}</p>
        </div>
      )}
    </div>
  );
}
