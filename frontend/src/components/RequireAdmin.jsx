/** 관리자 가드 — 미로그인 시 /login, 관리자 아니면 /dashboard 로 리다이렉트. */
import { Navigate, Outlet } from 'react-router-dom';
import { isAuthenticated, isAdmin } from '../api/client';

export default function RequireAdmin() {
  if (!isAuthenticated()) {
    return <Navigate to="/login" replace />;
  }
  if (!isAdmin()) {
    // 로그인은 했지만 관리자가 아님 → 대시보드로
    return <Navigate to="/dashboard" replace />;
  }
  return <Outlet />;
}
