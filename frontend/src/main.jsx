/** React 앱 마운트 — tokens.css 디자인 토큰 + App 라우터 */
import React from "react"
import ReactDOM from "react-dom/client"
import "./styles/tokens.css"
import App from "./App"

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode><App /></React.StrictMode>
)
