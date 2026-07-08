/**
 * 실마리 프론트엔드 라우팅 진입점.
 *
 * [화면 구역]
 *   공개: Landing, Login, Signup
 *   수사관 대시보드(DashboardLayout): 지도·챗봇·이력·탐지결과
 *   관리자(AdminLayout): /admin/:viewId
 *   API 테스트(DevLayout): /dev/*
 *
 * 레거시 경로 /alert, /result 는 /dashboard, /search-results 로 리다이렉트.
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
import DevLayout from './pages/dev/DevLayout';
import DevHub from './pages/dev/DevHub';
import DevHealthPage from './pages/dev/DevHealthPage';
import DevAuthPage from './pages/dev/DevAuthPage';
import DevMessagesPage from './pages/dev/DevMessagesPage';
import DevAlertPage from './pages/dev/DevAlertPage';
import DevSearchPage from './pages/dev/DevSearchPage';
import DevDisasterAlertsPage from './pages/dev/DevDisasterAlertsPage';
import DevResultPage from './pages/dev/DevResultPage';
import DevCctvPage from './pages/dev/DevCctvPage';
import DevChatbotPage from './pages/dev/DevChatbotPage';
import DevAdminPage from './pages/dev/DevAdminPage';
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

        <Route path="/dev" element={<DevLayout />}>
          <Route index element={<DevHub />} />
          <Route path="health" element={<DevHealthPage />} />
          <Route path="auth" element={<DevAuthPage />} />
          <Route path="messages" element={<DevMessagesPage />} />
          <Route path="alert" element={<DevAlertPage />} />
          <Route path="search" element={<DevSearchPage />} />
          <Route path="disaster" element={<DevDisasterAlertsPage />} />
          <Route path="result" element={<DevResultPage />} />
          <Route path="cctv" element={<DevCctvPage />} />
          <Route path="chatbot" element={<DevChatbotPage />} />
          <Route path="admin" element={<DevAdminPage />} />
        </Route>

        <Route path="/alert" element={<Navigate to="/dashboard" replace />} />
        <Route
          path="/result"
          element={<Navigate to="/search-results" replace />}
        />
      </Routes>
    </BrowserRouter>
  );
}
