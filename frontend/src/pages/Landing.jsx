/** 서비스 소개 랜딩 — 챗봇·안내문자 검색 방법 안내 + 로그인 유도 */
import { Link } from "react-router-dom"
import LandingHeader from "../components/LandingHeader"
import { ChatbotScreenPreview, AlertSearchScreenPreview } from "../components/LandingPreviews"
import "./Landing.css"

const METHODS = [
  {
    id: "01",
    title: "챗봇으로 검색하기",
    desc: "사진이나 인상착의를 입력하면 AI가 이미지를 분석해 유사한 사람을 찾아드려요.",
    steps: ["사진 또는 특징 입력", "AI 이미지 분석", "매칭 결과 확인"],
    preview: ChatbotScreenPreview,
  },
  {
    id: "02",
    title: "안전안내문자로 검색하기",
    desc: "재난·안전 안내문자에서 위치와 특징을 자동으로 추출해 실시간으로 매칭해요.",
    steps: ["안전안내문자 수신", "위치/특징 자동 추출", "자동 매칭 알림"],
    preview: AlertSearchScreenPreview,
    reverse: true,
  },
]

export default function Landing() {
  return (
    <div className="landing">
      <LandingHeader />

      <section className="landing-hero">
        <div className="landing-hero__inner">
          <p className="landing-hero__eyebrow">AI 이미지 분석 · 안전안내문자 연동</p>
          <h1 className="landing-hero__title">
            실종자를 찾는 가장 빠른 <span className="landing-hero__accent">실마리</span>
          </h1>
          <p className="landing-hero__desc">
            AI 이미지 분석과 안전안내문자 연동으로, 쉽고 빠르게 실종자를 찾을 수 있습니다.
          </p>
        </div>
      </section>

      <section id="landing-how" className="landing-how" aria-labelledby="landing-how-title">
        <div className="landing-how__inner">
          <header className="landing-how__head">
            <p className="landing-section__eyebrow landing-section__eyebrow--light">HOW IT WORKS</p>
            <h2 id="landing-how-title" className="landing-section__title landing-section__title--light">
              실마리는 이렇게 작동해요
            </h2>
            <p className="landing-section__subtitle landing-section__subtitle--light">
              두 가지 방법으로 쉽게 실종자를 찾을 수 있어요
            </p>
          </header>

          {METHODS.map((method) => {
            const Preview = method.preview
            return (
              <article
                key={method.id}
                className={[
                  "landing-method",
                  method.reverse && "landing-method--reverse",
                ].filter(Boolean).join(" ")}
              >
                <div className="landing-method__content">
                  <span className="landing-method__label landing-method__label--light">
                    METHOD {method.id}
                  </span>
                  <h3 className="landing-method__title landing-method__title--light">
                    {method.title}
                  </h3>
                  <p className="landing-method__desc landing-method__desc--light">
                    {method.desc}
                  </p>
                  <ol className="landing-method__steps">
                    {method.steps.map((step, i) => (
                      <li key={step}>
                        <span className="landing-method__step-num">{i + 1}</span>
                        {step}
                      </li>
                    ))}
                  </ol>
                </div>
                {Preview && (
                  <div className="landing-method__preview">
                    <Preview />
                  </div>
                )}
              </article>
            )
          })}
        </div>
      </section>

      <section className="landing-cta">
        <div className="landing-cta__inner">
          <h2 className="landing-cta__title">지금 바로 검색을 시작하세요</h2>
          <p className="landing-cta__desc">
            방법을 확인했다면 대시보드에서 실종자 검색을 바로 이용할 수 있어요.
          </p>
          <Link to="/dashboard" className="landing-btn landing-btn--primary landing-btn--lg">
            검색 시작하기
          </Link>
          <p className="landing-cta__alt">
            또는{" "}
            <Link to="/dashboard/chatbot">챗봇으로 바로 검색하기 →</Link>
          </p>
        </div>
      </section>

      <footer className="landing-footer">
        <p>© 실마리 · 공공 안전 데이터 기반 실종자 검색 서비스</p>
      </footer>
    </div>
  )
}
