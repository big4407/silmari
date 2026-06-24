import LandingHeader from "../components/LandingHeader"
import "./Landing.css"

export default function Landing() {
  return (
    <div className="landing">
      <LandingHeader />

      <main className="landing__main">
        <section className="landing__guide">
          <div className="landing__placeholder" aria-hidden="true">
            <span>챗봇 사용하는 화면 가이드 이미지</span>
          </div>
        </section>
        <section className="landing__guide">
          <div className="landing__placeholder" aria-hidden="true">
            <span>안전안내문자를 통한 사용 가이드 이미지</span>
          </div>
        </section>
      </main>

      <footer className="landing__footer" />
    </div>
  )
}
