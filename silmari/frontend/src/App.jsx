import { BrowserRouter, Routes, Route, NavLink, Navigate } from "react-router-dom"
import Dashboard from "./pages/Dashboard"
import CCTVUpload from "./pages/CCTVUpload"
import SearchResults from "./pages/SearchResults"
import "./App.css"

export default function App() {
  return (
    <BrowserRouter>
      <nav className="nav">
        <span className="nav__brand">실마리 Silmari</span>
        <NavLink to="/" end className={({ isActive }) => isActive ? "nav__link active" : "nav__link"}>대시보드</NavLink>
        <NavLink to="/cctv" className={({ isActive }) => isActive ? "nav__link active" : "nav__link"}>CCTV 분석</NavLink>
        <NavLink to="/search-results" className={({ isActive }) => isActive ? "nav__link active" : "nav__link"}>검색결과</NavLink>
      </nav>

      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/cctv" element={<CCTVUpload />} />
        <Route path="/search-results" element={<SearchResults />} />
        <Route path="/alert" element={<Navigate to="/cctv" replace />} />
        <Route path="/result" element={<Navigate to="/search-results" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
