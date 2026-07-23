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
import { useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import DashboardLayout from './components/DashboardLayout';
import Landing from './pages/Landing';
import Login from './pages/Login';
import Signup from './pages/Signup';
import FindAccountPage from './pages/FindAccountPage';
import Dashboard from './pages/Dashboard';
import ChatbotPage from './pages/ChatbotPage';
import SearchHistory from './pages/SearchHistory';
import SearchResults from './pages/SearchResults';
import CasesPage from './pages/CasesPage';
import CaseCreatePage from './pages/CaseCreatePage';
import AdminLayout from './pages/admin/AdminLayout';
import AdminViewPage from './pages/admin/AdminViewPage';
import RequireAuth from './components/RequireAuth';
import RequireAdmin from './components/RequireAdmin';
import { initAutoTitle } from './utils/autoTitle';
import './App.css';

export default function App() {
  // 말줄임표(ellipsis)로 잘린 요소에 마우스 올리면 자동으로 title 붙이기 —
  // 앱 전체(관리자 콘솔·대시보드·검색 이력 등)에 한 번만 등록.
  useEffect(() => initAutoTitle(), []);

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/login" element={<Login />} />
        <Route path="/signup" element={<Signup />} />
        <Route path="/find-account" element={<FindAccountPage />} />

        <Route element={<RequireAuth />}>
          <Route element={<DashboardLayout />}>
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/dashboard/chatbot" element={<ChatbotPage />} />
            <Route path="/dashboard/history" element={<SearchHistory />} />
            <Route path="/dashboard/cases" element={<CasesPage />} />
            <Route path="/dashboard/cases/new" element={<CaseCreatePage />} />
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
