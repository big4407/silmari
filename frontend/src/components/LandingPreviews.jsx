import "./LandingPreviews.css"

export function ChatbotScreenPreview() {
  return (
    <div className="screen-preview screen-preview--chatbot" aria-hidden="true">
      <div className="screen-preview__chrome">
        <span className="screen-preview__dot" />
        <span className="screen-preview__dot" />
        <span className="screen-preview__dot" />
        <span className="screen-preview__title">챗봇 검색</span>
      </div>
      <div className="screen-preview__body screen-preview__body--chat">
        <div className="preview-chat">
          <div className="preview-chat__msg preview-chat__msg--bot">
            안녕하세요! 실마리 챗봇입니다. 사진이나 인상착의를 입력해 주세요.
          </div>
          <div className="preview-chat__msg preview-chat__msg--user">
            검은 패딩 점퍼, 170cm 남성
          </div>
          <div className="preview-chat__msg preview-chat__msg--bot">
            특징을 분석했습니다. 유사 인물 3건을 찾았어요.
          </div>
          <div className="preview-chat__results">
            <div className="preview-chat__result">
              <span className="preview-chat__thumb" />
              <div className="preview-chat__result-body">
                <span className="preview-chat__score">92%</span>
                <small>매칭 · 서울 강남구 · 14:32</small>
              </div>
            </div>
            <div className="preview-chat__result">
              <span className="preview-chat__thumb" />
              <div className="preview-chat__result-body">
                <span className="preview-chat__score">87%</span>
                <small>매칭 · 서울 서초구 · 13:10</small>
              </div>
            </div>
          </div>
        </div>
        <div className="preview-chat__input">
          <span>사진 또는 특징을 입력하세요</span>
          <button type="button">전송</button>
        </div>
      </div>
    </div>
  )
}

export function AlertSearchScreenPreview() {
  return (
    <div className="screen-preview screen-preview--alert" aria-hidden="true">
      <div className="screen-preview__chrome">
        <span className="screen-preview__dot" />
        <span className="screen-preview__dot" />
        <span className="screen-preview__dot" />
        <span className="screen-preview__title">실종자 검색</span>
      </div>
      <div className="screen-preview__body screen-preview__body--dashboard">
        <div className="preview-dash__filters">
          <span className="preview-dash__label">조회 조건</span>
          <div className="preview-dash__row">
            <span className="preview-dash__field">2026-06-01 ~ 2026-06-29</span>
            <span className="preview-dash__field">서울특별시</span>
            <span className="preview-dash__btn">검색</span>
          </div>
        </div>
        <div className="preview-dash__content">
          <div className="preview-dash__map">
            <div className="preview-dash__map-region preview-dash__map-region--active" />
            <div className="preview-dash__map-region" />
            <div className="preview-dash__map-pin" />
          </div>
          <div className="preview-dash__alerts">
            <div className="preview-alert preview-alert--selected">
              <div className="preview-alert__head">
                <span>#1 · 실종</span>
                <span>2026-06-28</span>
              </div>
              <p>서울 강남구 · 검은 패딩, 170cm 남성…</p>
            </div>
            <div className="preview-alert">
              <div className="preview-alert__head">
                <span>#2</span>
                <span>2026-06-27</span>
              </div>
              <p>인천 연수구 인근 실종 신고. 회색 후드, 20대 여성…</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
