/**
 * 실마리 프론트엔드 라우팅 진입점.
 *
 * [화면 구역]
 *   공개: Landing, Login, Signup
 *   수사관 대시보드(DashboardLayout): 지도·챗봇·이력·탐지결과
 *   관리자(AdminLayout): /admin/:viewId
 *
 * 레거시 경로 /alert, /cctv, /result 는 현행 화면으로 리다이렉트.
 */
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import DashboardLayout from './components/DashboardLayout';
import Landing from './pages/Landing';
import Login from './pages/Login';
import Signup from './pages/Signup';
import Dashboard from './pages/Dashboard';
import ChatbotPage from './pages/ChatbotPage';
import SearchHistory from './pages/SearchHistory';
import SearchResults from './pages/SearchResults';
import AdminLayout from './pages/admin/AdminLayout';
import AdminViewPage from './pages/admin/AdminViewPage';
import RequireAuth from './components/RequireAuth';
import RequireAdmin from './components/RequireAdmin';
import './App.css';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/login" element={<Login />} />
        <Route path="/signup" element={<Signup />} />

        <Route element={<RequireAuth />}>
          <Route element={<DashboardLayout />}>
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/dashboard/chatbot" element={<ChatbotPage />} />
            <Route path="/dashboard/history" element={<SearchHistory />} />
            <Route path="/search-results" element={<SearchResults />} />
          </Route>
        </Route>

        <Route element={<RequireAdmin />}>
          <Route path="/admin" element={<AdminLayout />}>
            <Route index element={<AdminViewPage />} />
            <Route path=":viewId" element={<AdminViewPage />} />
          </Route>
        </Route>

        <Route path="/alert" element={<Navigate to="/dashboard" replace />} />
        <Route path="/cctv" element={<Navigate to="/dashboard" replace />} />
        <Route
          path="/result"
          element={<Navigate to="/search-results" replace />}
        />
      </Routes>
    </BrowserRouter>
  );
}
